"""
Isoform - icon engine (applicator / organizer)  ·  Windows
==========================================================
Applies and organizes a theme's icons over the Desktop shortcuts
(.lnk / .url). One engine for every theme; each theme only ships a
``theme.json``.

Safety model
------------
* ``--cleanup`` and ``--rename`` are **opt-in**; nothing destructive happens
  unless explicitly requested.
* ``--dry-run`` never writes, never refreshes Explorer, never prompts.
* Every change is backed up first; ``--restore <dir>`` reverts it.
* Duplicate detection uses the full shortcut identity (target + arguments +
  working directory), so distinct shortcuts are never treated as duplicates.
* Duplicate icon names are a hard error (``--allow-duplicate-icons`` to bypass).

CLI
---
    python icon_engine.py --config <theme.json> [--dry-run]
    python icon_engine.py --config <theme.json> --cleanup --rename --yes
    python icon_engine.py --config <theme.json> --organize --yes
    python icon_engine.py --restore <backup_dir>

Exit codes: 0 ok · 1 runtime error · 2 configuration error
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import sys
import time

INVISIBLE = "\u00a0"
REQUIRED_ICO_SIZES = (16, 32, 48, 64, 128, 256)
PERSIST_KEY_RE = re.compile(r"^[A-Za-z0-9._-]+$")

DEFAULTS = {
    "name": "Isoform Theme",
    "persist_key": None,
    "icons_dir": "Icons/ICO",
    "order": [],
}


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class ConfigError(Exception):
    """Invalid theme.json or persist_key."""


class IconNameError(Exception):
    """Two different icons resolve to the same key."""


class DependencyError(Exception):
    """Missing platform dependency (no auto-install by design)."""


# ---------------------------------------------------------------------------
# Platform / COM (lazy, never installs anything)
# ---------------------------------------------------------------------------
def _com():
    if sys.platform != "win32":
        raise DependencyError("Este motor solo funciona en Windows.")
    try:
        import pythoncom
        import win32com.client  # noqa: F401
    except ImportError as exc:
        raise DependencyError(
            "Falta la dependencia 'pywin32'. Instala el manifiesto fijado:\n"
            "    pip install -r requirements.txt\n"
            f"Detalle: {exc}"
        )
    return win32com, pythoncom


def _notify_file(path):
    import ctypes
    ctypes.windll.shell32.SHChangeNotify(
        0x00002000, 0x0001 | 0x1000,
        ctypes.c_wchar_p(path) if path else None, None,
    )


def _notify_shell():
    import ctypes
    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)


def _desktops():
    return [
        os.path.join(os.environ["USERPROFILE"], "Desktop"),
        os.path.join(os.environ.get("PUBLIC", r"C:\Users\Public"), "Desktop"),
    ]


def _shortcuts(desktop):
    return (glob.glob(os.path.join(desktop, "*.lnk")) +
            glob.glob(os.path.join(desktop, "*.url")))


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------
def validate_config(cfg, source):
    """Validate a raw theme dict and return a resolved config.

    Raises ConfigError with every problem found (not just the first).
    """
    errors = []

    name = cfg.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append("'name' debe ser texto no vacío")

    key = cfg.get("persist_key")
    if not isinstance(key, str) or not key:
        errors.append("'persist_key' es obligatorio")
    elif not PERSIST_KEY_RE.match(key) or key in {".", ".."}:
        errors.append("'persist_key' inválido: usa solo [A-Za-z0-9._-], sin separadores ni '..'")

    icons = cfg.get("icons_dir")
    if not isinstance(icons, str) or not icons.strip():
        errors.append("'icons_dir' debe ser texto no vacío")
    elif os.path.isabs(icons):
        errors.append("'icons_dir' no puede ser una ruta absoluta")
    elif os.path.normpath(icons).startswith(".."):
        errors.append("'icons_dir' no puede salir de la carpeta del tema")

    order = cfg.get("order", [])
    if not isinstance(order, list) or not all(isinstance(x, str) for x in order):
        errors.append("'order' debe ser una lista de strings")

    if errors:
        raise ConfigError(
            f"Configuración inválida en {source}:\n  - " + "\n  - ".join(errors)
        )

    theme_dir = os.path.normpath(os.path.dirname(os.path.abspath(source)))
    merged = dict(DEFAULTS)
    merged.update(cfg)
    merged["theme_dir"] = theme_dir
    merged["_source"] = source
    merged["icons_path"] = os.path.normpath(os.path.join(theme_dir, icons))

    if os.path.commonpath([theme_dir, os.path.abspath(merged["icons_path"])]) != theme_dir:
        raise ConfigError(f"'icons_dir' sale de la carpeta del tema: {icons}")

    return merged


def load_config(config_path):
    if not os.path.isfile(config_path):
        raise ConfigError(f"No existe el archivo de configuración: {config_path}")
    try:
        with open(config_path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"No se pudo leer {config_path}: {exc}")
    if not isinstance(raw, dict):
        raise ConfigError(f"{config_path} debe contener un objeto JSON")
    return validate_config(raw, config_path)


# ---------------------------------------------------------------------------
# Icon index (fails on duplicate keys)
# ---------------------------------------------------------------------------
def index_icons(icons_dir, allow_duplicates=False):
    """Map normalized icon key -> path. Duplicate keys are a hard error."""
    available = {}
    collisions = {}
    for root, _dirs, files in os.walk(icons_dir):
        for fname in files:
            if not fname.lower().endswith(".ico"):
                continue
            base = os.path.splitext(fname)[0].lower()
            full = os.path.join(root, fname)
            for key in {base, base.replace(" ", "")}:
                if key in available and available[key] != full:
                    collisions.setdefault(key, {available[key]}).add(full)
                else:
                    available[key] = full
    if collisions and not allow_duplicates:
        lines = [f"  - '{k}': {len(v)} archivos" for k, v in sorted(collisions.items())]
        raise IconNameError(
            "Nombres de icono duplicados (se sobrescribirían en silencio):\n"
            + "\n".join(lines)
            + "\nRenombra los archivos o usa --allow-duplicate-icons."
        )
    return available


# ---------------------------------------------------------------------------
# Shortcut identity / resolution
# ---------------------------------------------------------------------------
def _key_from_icon_path(raw):
    if not raw:
        return None
    candidate = raw.split(",")[0].strip().strip('"')
    if not candidate.lower().endswith(".ico"):
        return None
    return os.path.splitext(os.path.basename(candidate))[0].lower()


def _lookup(key, available):
    if not key:
        return None
    key = key.lower()
    return available.get(key) or available.get(key.replace(" ", ""))


def shortcut_identity(shell, path):
    """Full identity so distinct shortcuts are never deduped by mistake.

    .lnk -> target + arguments + working directory.
    .url -> the URL (Steam URLs normalized by AppID).
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".lnk":
        try:
            sc = shell.CreateShortcut(path)
            target = (sc.TargetPath or "").replace("/", "\\").strip().lower()
            if not target:
                return None
            args = (getattr(sc, "Arguments", "") or "").strip().lower()
            wd = (getattr(sc, "WorkingDirectory", "") or "").replace("/", "\\").strip().lower()
            return f"lnk|{target}|{args}|{wd}"
        except Exception:
            return None
    if ext == ".url":
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    if line.lower().startswith("url="):
                        url_val = line.split("=", 1)[1].strip().lower()
                        if url_val.startswith("steam://rungameid/"):
                            appid = "".join(c for c in url_val.split("steam://rungameid/")[1] if c.isdigit())
                            return f"url|steam:{appid}"
                        return f"url|{url_val}"
        except OSError:
            return None
    return None


def _resolve_lnk(sc, shortcut_path, available):
    name = os.path.splitext(os.path.basename(shortcut_path))[0]
    hit = _lookup(name, available)
    if hit:
        return hit
    hit = _lookup(_key_from_icon_path(sc.IconLocation), available)
    if hit:
        return hit
    target = (sc.TargetPath or "").replace("/", "\\")
    segs = {os.path.splitext(s)[0].lower() for s in target.split("\\") if s}
    for seg in sorted(segs, key=len, reverse=True):
        hit = _lookup(seg, available)
        if hit:
            return hit
    return None


def _resolve_url(lines, shortcut_path, available):
    for line in lines:
        if line.lower().startswith("url="):
            url_val = line.split("=", 1)[1].strip()
            if url_val.lower().startswith("steam://rungameid/"):
                appid = "".join(c for c in url_val.lower().split("steam://rungameid/")[1] if c.isdigit())
                mapping = STEAM_APP_MAP.get(appid)
                if mapping:
                    hit = _lookup(mapping, available)
                    if hit:
                        return hit
    name = os.path.splitext(os.path.basename(shortcut_path))[0]
    hit = _lookup(name, available)
    if hit:
        return hit
    for line in lines:
        if line.lower().startswith("iconfile="):
            hit = _lookup(_key_from_icon_path(line.split("=", 1)[1].strip()), available)
            if hit:
                return hit
    return None


STEAM_APP_MAP = {
    "730": "counter-strike-2", "550": "left 4 dead 2", "674940": "stick",
    "728880": "overcooked 2", "824270": "kovacks", "993090": "lossless scaling",
    "105600": "terraria", "431960": "wallpaper engine", "1281930": "tmodloader",
    "1460040": "mini cozy room", "1987080": "inside the backrooms", "3241660": "repo",
}


# ---------------------------------------------------------------------------
# Invisible names
# ---------------------------------------------------------------------------
def _read_url_lines(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        return fh.readlines()


def is_invisible_name(name):
    return len(name) > 0 and all(c == INVISIBLE for c in name)


def _unique_invisible_name(folder, ext):
    existing = {os.path.splitext(f)[0] for f in os.listdir(folder)}
    n = 1
    while INVISIBLE * n in existing:
        n += 1
    return os.path.join(folder, f"{INVISIBLE * n}{ext}")


# ---------------------------------------------------------------------------
# Backup / restore
# ---------------------------------------------------------------------------
def _backup_root(cfg):
    appdata = os.environ.get("LOCALAPPDATA", os.path.join(os.environ["USERPROFILE"], "AppData", "Local"))
    return os.path.join(appdata, "Icons_Engine", "backups", cfg["persist_key"])


def _write_backup(cfg, data):
    root = os.path.join(_backup_root(cfg), time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(root, exist_ok=True)
    with open(os.path.join(root, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    return root


def restore_backup(backup_dir, dry_run=False):
    manifest = os.path.join(backup_dir, "manifest.json")
    if not os.path.isfile(manifest):
        raise ConfigError(f"No hay manifest.json en {backup_dir}")
    with open(manifest, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    win32com, pythoncom = _com()
    pythoncom.CoInitialize()
    shell = win32com.client.Dispatch("WScript.Shell")
    restored = 0

    for path in data.get("created", []):
        if os.path.exists(path):
            if dry_run:
                print(f"  [DRY] Eliminaría {path}")
            else:
                os.remove(path)
                _notify_file(path)
                restored += 1

    for path, loc in data.get("lnk_icons", {}).items():
        if os.path.isfile(path):
            if dry_run:
                print(f"  [DRY] Restauraría icono de {path}")
            else:
                sc = shell.CreateShortcut(path)
                sc.IconLocation = loc
                sc.Save()
                _notify_file(path)
                restored += 1

    for path, text in data.get("url_files", {}).items():
        if os.path.isfile(path):
            if dry_run:
                print(f"  [DRY] Restauraría {path}")
            else:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text)
                _notify_file(path)
                restored += 1

    shell = None
    pythoncom.CoUninitialize()
    if not dry_run:
        _notify_shell()
    print(f"\nRestaurados {restored} elementos desde {backup_dir}.")
    return 0


# ---------------------------------------------------------------------------
# Icon publication (keeps shortcut links valid if the repo moves)
# ---------------------------------------------------------------------------
def _publish_icons(cfg):
    src = cfg["icons_path"]
    appdata = os.environ.get("LOCALAPPDATA", os.path.join(os.environ["USERPROFILE"], "AppData", "Local"))
    dest = os.path.join(appdata, "Icons_Engine", "Themes", cfg["persist_key"], "Icons")
    try:
        if os.path.exists(dest):
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        print(f"  [INFO] Iconos publicados en: {dest}")
        return dest
    except OSError as exc:
        print(f"  [WARN] No se pudo publicar ({exc}). Se usarán los iconos locales.")
        return src


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------
def apply_theme(cfg, dry_run=False, cleanup=False, rename=False, yes=False,
                allow_duplicate_icons=False):
    win32com, pythoncom = _com()

    if not os.path.isdir(cfg["icons_path"]):
        raise ConfigError(f"No se encontró la carpeta de iconos: {cfg['icons_path']}")

    if dry_run:
        icons_dir = cfg["icons_path"]
        print(f"  [DRY] usaría {icons_dir} (sin publicar)")
    else:
        icons_dir = _publish_icons(cfg)

    available = index_icons(icons_dir, allow_duplicates=allow_duplicate_icons)
    print(f"=== {cfg['name']} ===  ({len(available)} claves de icono)")

    pythoncom.CoInitialize()
    shell = win32com.client.Dispatch("WScript.Shell")

    # --- Plan -------------------------------------------------------------
    dup_deletions = []
    if cleanup:
        invisible, visible = {}, []
        for desktop in _desktops():
            if not os.path.isdir(desktop):
                continue
            for path in _shortcuts(desktop):
                identity = shortcut_identity(shell, path)
                if not identity:
                    continue
                if is_invisible_name(os.path.splitext(os.path.basename(path))[0]):
                    invisible[identity] = path
                else:
                    visible.append((identity, path))
        dup_deletions = [p for ident, p in visible if ident in invisible]

    apply_ops = []  # (path, ext, icon_path, label)
    unmatched = []
    for desktop in _desktops():
        if not os.path.isdir(desktop):
            continue
        for path in _shortcuts(desktop):
            ext = os.path.splitext(path)[1].lower()
            try:
                if ext == ".lnk":
                    sc = shell.CreateShortcut(path)
                    icon_path = _resolve_lnk(sc, path, available)
                    label = os.path.splitext(os.path.basename(sc.TargetPath or path))[0]
                    if icon_path:
                        apply_ops.append((path, ext, icon_path, label))
                    else:
                        unmatched.append(label)
                elif ext == ".url":
                    lines = _read_url_lines(path)
                    icon_path = _resolve_url(lines, path, available)
                    label = next((ln.strip()[4:] for ln in lines if ln.lower().startswith("url=")),
                                 os.path.basename(path))
                    if icon_path:
                        apply_ops.append((path, ext, icon_path, label))
                    else:
                        unmatched.append(label)
            except Exception as exc:
                print(f"  [FAIL] {os.path.basename(path)}: {exc}")

    # --- Report / dry-run -------------------------------------------------
    print(f"\nPlan: {len(apply_ops)} iconos · {len(dup_deletions)} duplicados a borrar"
          f" · renombrado={'sí' if rename else 'no'} · limpieza={'sí' if cleanup else 'no'}")
    if dry_run:
        for path, _ext, icon_path, label in apply_ops:
            print(f"  [DRY] {label} -> {os.path.basename(icon_path)}")
        for p in dup_deletions:
            print(f"  [DRY] eliminaría duplicado: {os.path.basename(p)}")
        if unmatched:
            print("  sin coincidencia:", ", ".join(sorted(set(unmatched))[:20]))
        shell = None
        pythoncom.CoUninitialize()
        return 0  # no writes, no refresh, no prompt

    if not apply_ops and not dup_deletions:
        print("Nada que hacer.")
        shell = None
        pythoncom.CoUninitialize()
        return 0

    if not yes:
        answer = input("¿Aplicar estos cambios? [y/N] ").strip().lower()
        if answer not in ("y", "yes", "s", "si", "sí"):
            print("Cancelado. Nada modificado.")
            shell = None
            pythoncom.CoUninitialize()
            return 0

    # --- Backup -----------------------------------------------------------
    backup = {"theme": cfg["persist_key"], "created": [], "lnk_icons": {}, "url_files": {}}

    # --- Cleanup ----------------------------------------------------------
    for path in dup_deletions:
        try:
            os.remove(path)
            _notify_file(path)
            print(f"  [CLEANUP] duplicado visible eliminado: {os.path.basename(path)}")
        except Exception as exc:
            print(f"  [WARN] no se pudo eliminar {os.path.basename(path)}: {exc}")

    # --- Apply icons ------------------------------------------------------
    applied = unchanged = 0
    for path, ext, icon_path, label in apply_ops:
        try:
            if ext == ".lnk":
                sc = shell.CreateShortcut(path)
                loc = f"{icon_path}, 0"
                if sc.IconLocation != loc:
                    backup["lnk_icons"][path] = sc.IconLocation
                    sc.IconLocation = loc
                    sc.Save()
                    _notify_file(path)
                    applied += 1
                    print(f"  [OK] {label}  ->  {os.path.basename(icon_path)}")
                else:
                    unchanged += 1
            else:
                lines = _read_url_lines(path)
                current = next((ln.split("=", 1)[1].strip()
                                for ln in lines if ln.lower().startswith("iconfile=")), None)
                if current != icon_path:
                    backup["url_files"][path] = "".join(lines)
                    has_icon = False
                    for i, line in enumerate(lines):
                        if line.lower().startswith("iconfile="):
                            lines[i] = f"IconFile={icon_path}\n"
                            has_icon = True
                        elif line.lower().startswith("iconindex="):
                            lines[i] = "IconIndex=0\n"
                    if not has_icon:
                        for i, line in enumerate(lines):
                            if line.strip().lower() == "[internetshortcut]":
                                lines.insert(i + 1, f"IconFile={icon_path}\n")
                                lines.insert(i + 2, "IconIndex=0\n")
                                break
                    with open(path, "w", encoding="utf-8") as fh:
                        fh.writelines(lines)
                    _notify_file(path)
                    applied += 1
                    print(f"  [OK] {label}  ->  {os.path.basename(icon_path)}")
                else:
                    unchanged += 1
        except Exception as exc:
            print(f"  [FAIL] {os.path.basename(path)}: {exc}")

    # --- Rename (opt-in) --------------------------------------------------
    renamed = 0
    if rename:
        # Re-scan because cleanup may have removed files
        for desktop in _desktops():
            if not os.path.isdir(desktop):
                continue
            for path in _shortcuts(desktop):
                base = os.path.splitext(os.path.basename(path))[0]
                if is_invisible_name(base):
                    continue
                new_path = _unique_invisible_name(desktop, os.path.splitext(path)[1].lower())
                try:
                    os.rename(path, new_path)
                    backup["created"].append(new_path)
                    _notify_file(path)
                    _notify_file(new_path)
                    renamed += 1
                    print(f"  [RENAME] '{base}' -> (invisible)")
                except Exception as exc:
                    print(f"  [WARN] no se pudo renombrar '{base}': {exc}")

    shell = None
    pythoncom.CoUninitialize()

    if backup["lnk_icons"] or backup["url_files"] or backup["created"]:
        where = _write_backup(cfg, backup)
        print(f"  [BACKUP] {where}")

    _notify_shell()
    print(f"\n¡Listo! Aplicados: {applied} | Ya correctos: {unchanged} | Renombrados: {renamed}"
          f" | Sin coincidencia: {len(unmatched)}")
    if unmatched:
        print("Sin coincidencia:", ", ".join(sorted(set(unmatched))))
    print("Si los iconos no se actualizaron, presiona F5 en el escritorio.")
    return 0


# ---------------------------------------------------------------------------
# Organize (former organize_desktop.py)
# ---------------------------------------------------------------------------
def organize_desktop(cfg, dry_run=False, yes=False):
    win32com, pythoncom = _com()
    pythoncom.CoInitialize()
    shell = win32com.client.Dispatch("WScript.Shell")
    order = [k.replace(" ", "").lower() for k in cfg.get("order", [])]

    items = []
    for desktop in _desktops():
        if not os.path.isdir(desktop):
            continue
        for path in _shortcuts(desktop):
            ext = os.path.splitext(path)[1].lower()
            key = None
            try:
                if ext == ".lnk":
                    key = _key_from_icon_path(shell.CreateShortcut(path).IconLocation)
                else:
                    lines = _read_url_lines(path)
                    current = next((ln.split("=", 1)[1].strip()
                                    for ln in lines if ln.lower().startswith("iconfile=")), None)
                    key = _key_from_icon_path(current)
            except Exception:
                continue
            if key:
                items.append({"path": path, "desktop": desktop, "ext": ext,
                              "key": key.replace(" ", "").lower()})

    if not items:
        print("No se encontraron accesos con iconos del pack aplicados.")
        shell = None
        pythoncom.CoUninitialize()
        return 0

    items.sort(key=lambda it: order.index(it["key"]) if it["key"] in order else len(order) + 100)
    print(f"=== Organizador: {cfg['name']} ===  ({len(items)} accesos)")

    if dry_run:
        for i, it in enumerate(items):
            print(f"  [DRY] #{i+1} {it['key']}")
        shell = None
        pythoncom.CoUninitialize()
        return 0

    if not yes and input("¿Reordenar y renombrar estos accesos? [y/N] ").strip().lower() not in ("y","yes","s","si","sí"):
        print("Cancelado.")
        shell = None
        pythoncom.CoUninitialize()
        return 0

    backup = {"theme": cfg["persist_key"], "created": [], "lnk_icons": {}, "url_files": {}}
    temp = []
    for idx, it in enumerate(items):
        tmp = os.path.join(it["desktop"], f"__temp_{idx}_{it['key']}{it['ext']}")
        try:
            os.rename(it["path"], tmp)
            _notify_file(it["path"])
            it["temp_path"] = tmp
            temp.append(it)
        except Exception as exc:
            print(f"  [ERROR] {os.path.basename(it['path'])}: {exc}")

    for idx, it in enumerate(temp):
        final = os.path.join(it["desktop"], f"{INVISIBLE * (idx + 1)}{it['ext']}")
        try:
            os.rename(it["temp_path"], final)
            backup["created"].append(final)
            _notify_file(it["temp_path"])
            _notify_file(final)
            print(f"  [#{idx+1}] {it['key']} -> (invisible)")
        except Exception as exc:
            print(f"  [ERROR] {it['key']}: {exc}")

    shell = None
    pythoncom.CoUninitialize()
    where = _write_backup(cfg, backup)
    _notify_shell()
    print(f"\n¡Listo! Backup: {where}")
    print("Ahora: clic derecho en el escritorio -> 'Ordenar por' -> 'Nombre'.")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser(config_path=None):
    p = argparse.ArgumentParser(description="Isoform - motor de iconos unificado")
    p.add_argument("--config", default=config_path, help="Ruta al theme.json")
    p.add_argument("--dry-run", action="store_true", help="No escribe, no refresca, no pregunta")
    p.add_argument("--cleanup", action="store_true", help="Borrar duplicados visibles (opt-in)")
    p.add_argument("--rename", action="store_true", help="Renombrar accesos a nombre invisible (opt-in)")
    p.add_argument("--organize", action="store_true", help="Reordenar accesos aplicados")
    p.add_argument("--yes", action="store_true", help="No pedir confirmación")
    p.add_argument("--allow-duplicate-icons", action="store_true",
                   help="Permitir nombres de icono duplicados (se sobrescriben)")
    p.add_argument("--restore", metavar="DIR", help="Restaurar desde un backup")
    return p


def run_cli(config_path=None, argv=None):
    args = build_parser(config_path).parse_args(argv)
    try:
        if args.restore:
            return restore_backup(args.restore, dry_run=args.dry_run)
        if not args.config:
            raise ConfigError("Falta --config (ruta al theme.json)")
        cfg = load_config(args.config)
        if args.organize:
            return organize_desktop(cfg, dry_run=args.dry_run, yes=args.yes)
        return apply_theme(cfg, dry_run=args.dry_run, cleanup=args.cleanup,
                           rename=args.rename, yes=args.yes,
                           allow_duplicate_icons=args.allow_duplicate_icons)
    except ConfigError as exc:
        print(f"[CONFIG] {exc}", file=sys.stderr)
        return 2
    except DependencyError as exc:
        print(f"[DEPENDENCIA] {exc}", file=sys.stderr)
        return 1
    except IconNameError as exc:
        print(f"[ICONOS] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run_cli())
