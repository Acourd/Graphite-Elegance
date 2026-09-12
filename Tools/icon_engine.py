"""
Isoform - icon engine (applicator / organizer)  ·  Windows
==========================================================
Applies and organizes a theme's icons over the Desktop shortcuts
(.lnk / .url). One engine for every theme; each theme only ships a
``theme.json``.

Safety model
------------
* ``--cleanup`` and ``--rename`` are **opt-in**; deterministic by default.
* ``--dry-run`` never writes, never refreshes Explorer, never prompts.
* A backup is written **before** any mutation (icon changes, deletions and
  renames all included). ``--restore <dir>`` validates the manifest schema,
  restricts every path to an allowed Desktop root, and restores from the
  backed-up files (including the original shortcut names).
* Rename/organize only touch shortcuts that belong to the active theme.
* Duplicate detection uses the full shortcut identity (target + arguments +
  working directory), so distinct shortcuts are never treated as duplicates.
* Duplicate icon names are a hard error (``--allow-duplicate-icons`` bypasses).
* No dependency is installed automatically; ``pywin32`` comes from the pinned
  manifest.

CLI
---
    python icon_engine.py --config <theme.json> [--dry-run]
    python icon_engine.py --config <theme.json> --cleanup --rename --yes
    python icon_engine.py --config <theme.json> --organize --yes
    python icon_engine.py --restore <backup_dir>

Exit codes: 0 ok · 1 runtime/dependency error · 2 configuration error
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import sys
import time
import uuid

INVISIBLE = "\u00a0"
REQUIRED_ICO_SIZES = (16, 32, 48, 64, 128, 256)
PERSIST_KEY_RE = re.compile(r"^[A-Za-z0-9._-]+$")
ALLOWED_CONFIG_KEYS = {"name", "persist_key", "icons_dir", "order"}
BACKUP_SCHEMA = 2

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


class BackupError(Exception):
    """Invalid or unsafe backup manifest."""


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
    if sys.platform != "win32":
        return
    import ctypes
    ctypes.windll.shell32.SHChangeNotify(
        0x00002000, 0x0001 | 0x1000,
        ctypes.c_wchar_p(path) if path else None, None,
    )


def _notify_shell():
    if sys.platform != "win32":
        return
    import ctypes
    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# Desktop roots
# ---------------------------------------------------------------------------
def desktop_dirs():
    """Allowed Desktop roots. Overridable for tests via ISO_DESKTOP_DIRS."""
    override = os.environ.get("ISO_DESKTOP_DIRS")
    if override:
        return [os.path.abspath(p) for p in override.split(os.pathsep) if p]
    home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    public = os.environ.get("PUBLIC", r"C:\Users\Public")
    return [
        os.path.abspath(os.path.join(home, "Desktop")),
        os.path.abspath(os.path.join(public, "Desktop")),
    ]


def appdata_dir():
    """Per-user data dir. Works off Windows too (never raises KeyError)."""
    appdata = os.environ.get("LOCALAPPDATA")
    if appdata:
        return appdata
    home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    return os.path.join(home, "AppData", "Local")


def is_within(path, roots):
    ap = os.path.realpath(path)
    for root in roots:
        root = os.path.realpath(root)
        try:
            if ap != root and os.path.commonpath([ap, root]) == root:
                return True
        except ValueError:
            continue
    return False


def _shortcuts(desktop):
    return (glob.glob(os.path.join(desktop, "*.lnk")) +
            glob.glob(os.path.join(desktop, "*.url")))


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------
_WIN_ABS_RE = re.compile(r"^[A-Za-z]:[\\/]")


def looks_absolute(path):
    """Absolute on the current platform *and* for Windows-style paths."""
    return os.path.isabs(path) or bool(_WIN_ABS_RE.match(path)) or path.startswith("\\\\")


def has_traversal(path):
    """True for '..' path components regardless of separator style."""
    return any(part == ".." for part in path.replace("\\", "/").split("/"))


def validate_config(cfg, source):
    """Validate a raw theme dict and return a resolved config."""
    errors = []

    unknown = set(cfg) - ALLOWED_CONFIG_KEYS
    if unknown:
        errors.append(f"claves desconocidas: {', '.join(sorted(unknown))}")

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
    elif looks_absolute(icons):
        errors.append("'icons_dir' no puede ser una ruta absoluta")
    elif has_traversal(icons):
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
        with open(config_path, "r", encoding="utf-8-sig") as fh:
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
    available = {}
    collisions = {}
    for root, _dirs, files in os.walk(icons_dir):
        for fname in sorted(files):
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
def _split_icon_ref(raw):
    """Split an IconLocation/IconFile value into (path, index).

    Commas inside the path are preserved; only a trailing ',<int>' is the index.
    """
    if not raw:
        return None, None
    text = raw.strip()
    quoted = re.match(r'^"(?P<path>.*)"\s*,\s*(?P<index>-?\d+)$', text)
    if quoted:
        return quoted.group("path"), int(quoted.group("index"))
    plain = re.match(r"^(?P<path>.*),\s*(?P<index>-?\d+)$", text)
    if plain:
        return plain.group("path"), int(plain.group("index"))
    only_quoted = re.match(r'^"(?P<path>.*)"$', text)
    if only_quoted:
        return only_quoted.group("path"), None
    return text, None


def _key_from_icon_path(raw):
    path, _index = _split_icon_ref(raw)
    if not path or not path.lower().endswith(".ico"):
        return None
    name = path.replace("\\", "/").rsplit("/", 1)[-1]
    return os.path.splitext(name)[0].lower()


def _icon_file_from_raw(raw):
    """Path part of an IconLocation/IconFile value (index stripped)."""
    path, _index = _split_icon_ref(raw)
    return path or None


def _lookup(key, available):
    if not key:
        return None
    key = key.lower()
    return available.get(key) or available.get(key.replace(" ", ""))


def _norm_win_path(value):
    """Case/separator normalization for Windows paths, regardless of host OS."""
    return (value or "").replace("/", "\\").strip().lower()


def _same_icon_location(current, target_path, ext):
    path, index = _split_icon_ref(current)
    if not path or _norm_win_path(path) != _norm_win_path(target_path):
        return False
    if ext == ".lnk":
        return index in (None, 0)
    return True


def shortcut_identity(shell, path):
    """Full identity so distinct shortcuts are never deduped by mistake."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".lnk":
        try:
            sc = shell.CreateShortcut(path)
            target = _norm_win_path(sc.TargetPath)
            if not target:
                return None
            # Windows paths are case-insensitive; arguments are not.
            args = (getattr(sc, "Arguments", "") or "").strip()
            wd = _norm_win_path(getattr(sc, "WorkingDirectory", ""))
            return f"lnk|{target}|{args}|{wd}"
        except Exception:
            return None
    if ext == ".url":
        try:
            for line in _read_url(path)[0]:
                if line.lower().startswith("url="):
                    url_val = line.split("=", 1)[1].strip()
                    if url_val.lower().startswith("steam://rungameid/"):
                        appid = "".join(c for c in url_val.lower().split("steam://rungameid/")[1] if c.isdigit())
                        return f"url|steam:{appid}"
                    return f"url|{url_val}"
        except OSError:
            return None
    return None


STEAM_APP_MAP = {
    "730": "counter-strike-2", "550": "left 4 dead 2", "674940": "stick",
    "728880": "overcooked 2", "824270": "kovacks", "993090": "lossless scaling",
    "105600": "terraria", "431960": "wallpaper engine", "1281930": "tmodloader",
    "1460040": "mini cozy room", "1987080": "inside the backrooms", "3241660": "repo",
}

GENERIC_STEMS = {
    "app", "application", "bootstrapper", "client", "helper", "index", "install",
    "installer", "launcher", "loader", "main", "portal", "run", "service", "setup",
    "start", "startup", "uninstall", "uninstaller", "update", "updater",
}


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
        if seg in GENERIC_STEMS:
            continue
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


# ---------------------------------------------------------------------------
# Invisible names
# ---------------------------------------------------------------------------
def _read_url(path):
    """Return (lines, encoding), tolerating UTF-16 and legacy encodings."""
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        encoding = "utf-16"
    elif data[:3] == b"\xef\xbb\xbf":
        encoding = "utf-8-sig"
    else:
        encoding = "utf-8"
    try:
        text = data.decode(encoding)
    except UnicodeDecodeError:
        encoding = "cp1252"
        text = data.decode(encoding, errors="replace")
    return text.splitlines(keepends=True), encoding


def _read_url_lines(path):
    return _read_url(path)[0]


def is_invisible_name(name):
    return len(name) > 0 and all(c == INVISIBLE for c in name)


def _unique_invisible_name(folder, ext, used):
    n = 1
    while (INVISIBLE * n + ext) in used:
        n += 1
    return os.path.join(folder, INVISIBLE * n + ext)


# ---------------------------------------------------------------------------
# Backup / restore
# ---------------------------------------------------------------------------
def _backup_base(cfg):
    appdata = appdata_dir()
    return os.path.join(appdata, "Icons_Engine", "backups", cfg["persist_key"])


def _new_backup_dir(cfg):
    """Create a unique backup directory (timestamp + uuid, exclusive)."""
    root = _backup_base(cfg)
    for _ in range(10):
        candidate = os.path.join(root, f"{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}")
        try:
            os.makedirs(candidate, exist_ok=False)
            return candidate
        except FileExistsError:
            continue
    raise BackupError("No se pudo crear un directorio de backup único")


def create_backup(cfg, entries):
    """Copy every affected shortcut into a timestamped backup and write a
    manifest. ``entries`` is a list of dicts: {op, path[, new_path]}."""
    base = _new_backup_dir(cfg)
    files_dir = os.path.join(base, "files")
    os.makedirs(files_dir, exist_ok=True)
    manifest_entries = []
    for i, entry in enumerate(entries):
        src = entry["path"]
        if not os.path.isfile(src):
            continue
        rel = f"{i:04d}_{os.path.basename(src)}"
        copied = os.path.join(files_dir, rel)
        shutil.copy2(src, copied)
        item = {"op": entry["op"], "path": src, "backup": rel, "sha256": sha256_file(copied)}
        if entry["op"] == "rename":
            item["new_path"] = entry["new_path"]
        manifest_entries.append(item)
    manifest = {
        "schema": BACKUP_SCHEMA,
        "theme": cfg["persist_key"],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "entries": manifest_entries,
    }
    with open(os.path.join(base, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    return base


def _safe_backup_file(backup_dir, rel):
    parts = rel.replace("\\", "/").split("/")
    if os.path.isabs(rel) or ".." in parts or not rel:
        raise BackupError(f"Ruta de backup insegura: {rel!r}")
    files_root = os.path.abspath(os.path.join(backup_dir, "files"))
    full = os.path.abspath(os.path.join(files_root, rel))
    if os.path.commonpath([full, files_root]) != files_root:
        raise BackupError(f"Ruta de backup fuera de la carpeta: {rel!r}")
    return full


def validate_manifest(data, backup_dir):
    """Validate schema and restrict every path to an allowed Desktop root."""
    if not isinstance(data, dict):
        raise BackupError("El manifiesto no es un objeto JSON")
    schema = data.get("schema")
    if schema not in (1, BACKUP_SCHEMA):
        raise BackupError(f"Esquema de backup no soportado: {schema!r}")
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise BackupError("El manifiesto no tiene 'entries'")

    roots = desktop_dirs()
    for entry in entries:
        if not isinstance(entry, dict):
            raise BackupError("Entrada de manifiesto inválida")
        op = entry.get("op")
        if op not in ("modify", "delete", "rename"):
            raise BackupError(f"Operación desconocida: {op!r}")
        path = entry.get("path")
        if not isinstance(path, str) or not is_within(path, roots):
            raise BackupError(f"Ruta restaurable fuera del escritorio permitido: {path!r}")
        digest = entry.get("sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise BackupError("Falta el hash SHA-256 de la entrada de backup")
        post = entry.get("post_sha256")
        if post is not None and (not isinstance(post, str)
                                 or not re.fullmatch(r"[0-9a-f]{64}", post)):
            raise BackupError("Hash post-aplicación inválido")
        _safe_backup_file(backup_dir, entry.get("backup", ""))
        if op == "rename":
            new_path = entry.get("new_path")
            if not isinstance(new_path, str) or not is_within(new_path, roots):
                raise BackupError(f"'new_path' fuera del escritorio permitido: {new_path!r}")
    return entries


_RESTORE_ORPHAN_RE = re.compile(r"\.isoform-restore-[0-9a-fA-F]{8}$")
RESTORE_ORPHAN_MIN_AGE = 300  # seconds; never touch a likely-active restore


def sweep_restore_orphans(min_age=RESTORE_ORPHAN_MIN_AGE):
    """Best-effort removal of stale restore temp files.

    Strictly limited to ``<name>.isoform-restore-<8 hex>`` that are *direct*
    children of an allowed Desktop root, and only when older than ``min_age``
    seconds, so an active restore is never disturbed. Returns the count removed.
    """
    removed = 0
    now = time.time()
    for desktop in desktop_dirs():
        if not os.path.isdir(desktop):
            continue
        try:
            entries = os.listdir(desktop)
        except OSError:
            continue
        for name in entries:
            if not _RESTORE_ORPHAN_RE.search(name):
                continue
            path = os.path.join(desktop, name)
            if not os.path.isfile(path):
                continue
            try:
                if now - os.path.getmtime(path) < min_age:
                    continue
                os.remove(path)
                removed += 1
            except OSError:
                continue
    if removed:
        print(f"  [INFO] Limpiados {removed} temporales de restauración huérfanos.")
    return removed


def _snapshot_file(path):
    if not os.path.isfile(path):
        return None
    snap = f"{path}.isoform-restore-{uuid.uuid4().hex[:8]}"
    shutil.copy2(path, snap)
    return snap


def _restore_snapshot(path, snap):
    try:
        if snap is None:
            if os.path.isfile(path):
                os.remove(path)
        else:
            os.replace(snap, path)
        _notify_file(path)
        return True
    except OSError as exc:
        print(f"  [ERROR] no se pudo revertir {path}: {exc}")
        return False


def record_post_hashes(backup_dir, renames):
    """Pin the expected content of renamed shortcuts after a successful apply."""
    manifest_path = os.path.join(backup_dir, "manifest.json")
    try:
        with open(manifest_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return
    by_new = {os.path.normcase(r["new_path"]): r for r in renames}
    for entry in data.get("entries", []):
        if entry.get("op") != "rename":
            continue
        target = by_new.get(os.path.normcase(entry.get("new_path", "")))
        if target and os.path.isfile(target["new_path"]):
            entry["post_sha256"] = sha256_file(target["new_path"])
    try:
        with open(manifest_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
    except OSError:
        pass


def _owns_backup_file(path, expected):
    if not os.path.isfile(path):
        return False
    try:
        return sha256_file(path) == expected
    except OSError:
        return False


def restore_backup(backup_dir, dry_run=False):
    manifest_path = os.path.join(backup_dir, "manifest.json")
    if not os.path.isfile(manifest_path):
        raise BackupError(f"No hay manifest.json en {backup_dir}")
    with open(manifest_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    entries = validate_manifest(data, backup_dir)

    # Pre-validate every file (existence AND hash) before any mutation.
    resolved = []
    for entry in entries:
        backup_file = _safe_backup_file(backup_dir, entry["backup"])
        if not os.path.isfile(backup_file):
            raise BackupError(f"Falta el archivo de backup: {backup_file}")
        digest = sha256_file(backup_file)
        if digest != entry["sha256"]:
            raise BackupError(f"El archivo de backup {entry['backup']} no coincide con su hash")
        resolved.append((entry, backup_file, digest))

    if dry_run:
        for entry, _backup, _digest in resolved:
            print(f"  [DRY] restauraría {entry['op']}: {entry['path']}")
        return 0

    # Clear stale temporaries from a previous interrupted restore before staging.
    sweep_restore_orphans()

    # Phase 1: stage every restore next to its destination (all-or-nothing).
    # If any copy or hash fails, nothing has been replaced yet.
    staged = []
    try:
        for entry, backup_file, backup_hash in resolved:
            target = entry["path"]
            os.makedirs(os.path.dirname(target), exist_ok=True)
            temp = f"{target}.isoform-restore-{uuid.uuid4().hex[:8]}"
            shutil.copy2(backup_file, temp)
            if sha256_file(temp) != backup_hash:
                try:
                    os.remove(temp)
                except OSError:
                    pass
                raise BackupError(f"la copia de staging no coincide: {backup_file}")
            staged.append((entry, backup_hash, temp))
    except OSError as exc:
        for _entry, _hash, temp in staged:
            try:
                os.remove(temp)
            except OSError:
                pass
        raise BackupError(f"No se pudo preparar la restauración (nada restaurado): {exc}")
    except BackupError:
        for _entry, _hash, temp in staged:
            try:
                os.remove(temp)
            except OSError:
                pass
        raise

    # Phase 2: move the staged files into place (rename, no copy). Any failure
    # rolls back every entry already touched, so nothing is left half-restored.
    restored = 0
    failures = 0
    applied = []
    rollback_errors = []
    for index, (entry, backup_hash, temp) in enumerate(staged):
        try:
            if entry["op"] == "rename":
                new_path = entry["new_path"]
                if os.path.exists(new_path):
                    post = entry.get("post_sha256")
                    if not post or not _owns_backup_file(new_path, post):
                        raise BackupError(
                            f"conflicto: {new_path} no es el archivo del rename aprobado; no se toca")
                    applied.append((new_path, _snapshot_file(new_path)))
                    os.remove(new_path)
                    _notify_file(new_path)
            applied.append((entry["path"], _snapshot_file(entry["path"])))
            os.replace(temp, entry["path"])
            if sha256_file(entry["path"]) != backup_hash:
                raise BackupError("los bytes restaurados no coinciden con el backup")
            _notify_file(entry["path"])
            restored += 1
        except (OSError, BackupError) as exc:
            failures += 1
            print(f"  [WARN] no se pudo restaurar {entry['path']}: {exc}")
            for _e, _h, leftover in staged[index:]:
                try:
                    os.remove(leftover)
                except OSError:
                    pass
            for path, snap in reversed(applied):
                if not _restore_snapshot(path, snap):
                    rollback_errors.append(path)
            applied = []
            break
    if rollback_errors:
        raise BackupError(
            "reversión incompleta; conserva los archivos .isoform-restore-* para "
            "recuperación: " + ", ".join(rollback_errors))
    if not failures:
        for _path, snap in applied:
            if snap and os.path.exists(snap):
                try:
                    os.remove(snap)
                except OSError:
                    pass
    _notify_shell()
    print(f"\nRestaurados {restored} elementos desde {backup_dir}.")
    if failures:
        print(f"Fallos: {failures}")
    return 1 if failures else 0


# ---------------------------------------------------------------------------
# Icon publication (keeps shortcut links valid if the repo moves)
# ---------------------------------------------------------------------------
def _published_icons_dir(cfg):
    return os.path.join(appdata_dir(), "Icons_Engine", "Themes", cfg["persist_key"], "Icons")


def _publish_icons(cfg):
    src = cfg["icons_path"]
    dest = _published_icons_dir(cfg)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    staging = f"{dest}.staging-{uuid.uuid4().hex[:8]}"
    previous = f"{dest}.previous"

    try:
        shutil.copytree(src, staging)          # build staging first (dest untouched)
    except OSError as exc:
        shutil.rmtree(staging, ignore_errors=True)
        print(f"  [WARN] No se pudo publicar ({exc}). Se usarán los iconos locales.")
        return src

    moved_previous = False
    try:
        if os.path.exists(previous):
            shutil.rmtree(previous, ignore_errors=True)
        if os.path.exists(dest):
            os.rename(dest, previous)          # keep the previous tree for recovery
            moved_previous = True
        os.rename(staging, dest)               # atomic-ish swap
    except OSError as exc:
        rolled_back = not moved_previous
        if moved_previous and not os.path.exists(dest) and os.path.exists(previous):
            try:
                os.rename(previous, dest)      # roll back so nothing is lost
                rolled_back = True
            except OSError as rollback_exc:
                print(f"  [ERROR] No se pudo revertir la publicación ({rollback_exc}). "
                      f"El árbol anterior queda en: {previous}", file=sys.stderr)
        shutil.rmtree(staging, ignore_errors=True)
        if rolled_back:
            print(f"  [WARN] No se pudo publicar ({exc}). Se usarán los iconos locales.")
        return src
    print(f"  [INFO] Iconos publicados en: {dest}")
    return dest


def _tree_drift(src, dest):
    """Relative paths of icons missing from (or different in) the published tree."""
    drift = []
    src_rel = set()
    for root, _dirs, files in os.walk(src):
        for fname in sorted(files):
            if not fname.lower().endswith(".ico"):
                continue
            full = os.path.join(root, fname)
            rel = os.path.relpath(full, src)
            src_rel.add(os.path.normcase(rel))
            other = os.path.join(dest, rel)
            if not os.path.isfile(other):
                drift.append(rel)
                continue
            try:
                if os.path.getsize(other) != os.path.getsize(full) or sha256_file(other) != sha256_file(full):
                    drift.append(rel)
            except OSError:
                drift.append(rel)
    for root, _dirs, files in os.walk(dest):
        for fname in sorted(files):
            if not fname.lower().endswith(".ico"):
                continue
            rel = os.path.relpath(os.path.join(root, fname), dest)
            if os.path.normcase(rel) not in src_rel:
                drift.append(rel)
    return drift


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------
def plan_apply(cfg, available, shell, target_dir, cleanup=False, rename=False):
    """Return (dup_deletions, changes, renames, unmatched).

    ``target_dir`` is the published icon directory the shortcuts should point to;
    the comparison uses it so re-applying an already-published theme is a no-op.
    """
    dup_deletions = []
    if cleanup:
        invisible, visible = {}, []
        for desktop in desktop_dirs():
            if not os.path.isdir(desktop):
                continue
            for path in sorted(_shortcuts(desktop)):
                identity = shortcut_identity(shell, path)
                if not identity:
                    continue
                if is_invisible_name(os.path.splitext(os.path.basename(path))[0]):
                    invisible[identity] = path
                else:
                    visible.append((identity, path))
        dup_deletions = [p for ident, p in visible if ident in invisible]
    dup_set = set(os.path.normcase(p) for p in dup_deletions)

    matched = []
    unmatched = []
    for desktop in desktop_dirs():
        if not os.path.isdir(desktop):
            continue
        for path in sorted(_shortcuts(desktop)):
            if os.path.normcase(path) in dup_set:
                continue
            ext = os.path.splitext(path)[1].lower()
            try:
                if ext == ".lnk":
                    sc = shell.CreateShortcut(path)
                    icon_path = _resolve_lnk(sc, path, available)
                    label = os.path.splitext(os.path.basename(sc.TargetPath or path))[0]
                    current = sc.IconLocation
                else:
                    lines = _read_url_lines(path)
                    icon_path = _resolve_url(lines, path, available)
                    label = next((ln.strip()[4:] for ln in lines if ln.lower().startswith("url=")),
                                 os.path.basename(path))
                    current = next((ln.split("=", 1)[1].strip()
                                    for ln in lines if ln.lower().startswith("iconfile=")), None)
            except Exception as exc:
                print(f"  [FAIL] {os.path.basename(path)}: {exc}")
                continue
            if not icon_path:
                unmatched.append(label)
                continue
            rel = os.path.relpath(icon_path, cfg["icons_path"])
            target_path = os.path.join(target_dir, rel)
            matched.append({"path": path, "ext": ext, "icon_path": icon_path,
                            "icon_rel": rel, "target_path": target_path,
                            "label": label,
                            "changed": not _same_icon_location(current, target_path, ext)})

    changes = [m for m in matched if m["changed"]]
    renames = []
    if rename:
        used = {}
        for m in matched:
            desktop = os.path.dirname(m["path"])
            if desktop not in used:
                used[desktop] = set(os.listdir(desktop))
            base = os.path.splitext(os.path.basename(m["path"]))[0]
            if is_invisible_name(base):
                continue
            new_path = _unique_invisible_name(desktop, m["ext"], used[desktop])
            used[desktop].add(os.path.basename(new_path))
            renames.append({"path": m["path"], "new_path": new_path})
    return dup_deletions, changes, renames, unmatched


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------
def apply_theme(cfg, dry_run=False, cleanup=False, rename=False, yes=False,
                allow_duplicate_icons=False):
    win32com, pythoncom = _com()

    if not os.path.isdir(cfg["icons_path"]):
        raise ConfigError(f"No se encontró la carpeta de iconos: {cfg['icons_path']}")

    # Plan against the source tree (read-only); nothing is published yet.
    available = index_icons(cfg["icons_path"], allow_duplicates=allow_duplicate_icons)
    print(f"=== {cfg['name']} ===  ({len(available)} claves de icono)")

    published_dir = _published_icons_dir(cfg)
    drift = _tree_drift(cfg["icons_path"], published_dir)

    pythoncom.CoInitialize()
    shell = win32com.client.Dispatch("WScript.Shell")
    dup_deletions, changes, renames, unmatched = plan_apply(
        cfg, available, shell, published_dir, cleanup=cleanup, rename=rename)

    print(f"\nPlan: {len(changes)} iconos · {len(dup_deletions)} duplicados a borrar"
          f" · {len(renames)} renombrados · {len(drift)} assets a sincronizar"
          f" · limpieza={'sí' if cleanup else 'no'}"
          f" · renombrado={'sí' if rename else 'no'}")
    if dry_run:
        for c in changes:
            print(f"  [DRY] {c['label']} -> {os.path.basename(c['target_path'])}")
        for p in dup_deletions:
            print(f"  [DRY] eliminaría duplicado: {os.path.basename(p)}")
        for r in renames:
            print(f"  [DRY] renombraría {os.path.basename(r['path'])}")
        for rel in drift:
            print(f"  [DRY] publicaría {rel}")
        if unmatched:
            print("  sin coincidencia:", ", ".join(sorted(set(unmatched))[:20]))
        shell = None
        pythoncom.CoUninitialize()
        return 0

    total = len(changes) + len(dup_deletions) + len(renames)
    if total == 0 and not drift:
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

    # Publish only after confirmation, via staging + atomic replace. Assets are
    # re-synced even when no shortcut needs changes (repairs a damaged or stale
    # published tree) and never trigger a shortcut backup by themselves.
    published = published_dir
    if drift:
        published = _publish_icons(cfg)
        if os.path.normcase(published) != os.path.normcase(published_dir):
            shell = None
            pythoncom.CoUninitialize()
            return 1
    for c in changes:
        c["icon_path"] = os.path.join(published, c["icon_rel"])

    if total == 0:
        _notify_shell()
        shell = None
        pythoncom.CoUninitialize()
        print(f"\nIconos publicados sincronizados: {len(drift)} archivos.")
        return 0

    # --- Backup BEFORE any mutation (merging rename over modify per path) ---
    by_path = {}
    for p in dup_deletions:
        by_path[p] = {"op": "delete", "path": p}
    for c in changes:
        by_path.setdefault(c["path"], {"op": "modify", "path": c["path"]})
    for r in renames:
        by_path[r["path"]] = {"op": "rename", "path": r["path"], "new_path": r["new_path"]}
    backup_dir = create_backup(cfg, list(by_path.values()))

    # --- Execute ----------------------------------------------------------
    failures = 0
    for p in dup_deletions:
        try:
            os.remove(p)
            _notify_file(p)
            print(f"  [CLEANUP] duplicado visible eliminado: {os.path.basename(p)}")
        except OSError as exc:
            failures += 1
            print(f"  [WARN] no se pudo eliminar {os.path.basename(p)}: {exc}")

    applied = 0
    for c in changes:
        try:
            if c["ext"] == ".lnk":
                sc = shell.CreateShortcut(c["path"])
                sc.IconLocation = f"{c['icon_path']}, 0"
                sc.Save()
            else:
                lines, encoding = _read_url(c["path"])
                has_icon = False
                for i, line in enumerate(lines):
                    if line.lower().startswith("iconfile="):
                        lines[i] = f"IconFile={c['icon_path']}\n"
                        has_icon = True
                    elif line.lower().startswith("iconindex="):
                        lines[i] = "IconIndex=0\n"
                if not has_icon:
                    for i, line in enumerate(lines):
                        if line.strip().lower() == "[internetshortcut]":
                            lines.insert(i + 1, f"IconFile={c['icon_path']}\n")
                            lines.insert(i + 2, "IconIndex=0\n")
                            break
                with open(c["path"], "w", encoding=encoding) as fh:
                    fh.writelines(lines)
            _notify_file(c["path"])
            applied += 1
            print(f"  [OK] {c['label']}  ->  {os.path.basename(c['icon_path'])}")
        except Exception as exc:
            failures += 1
            print(f"  [FAIL] {os.path.basename(c['path'])}: {exc}")

    renamed = 0
    renamed_ok = []
    for r in renames:
        try:
            os.rename(r["path"], r["new_path"])
            renamed_ok.append(r)
            _notify_file(r["path"])
            _notify_file(r["new_path"])
            renamed += 1
            print(f"  [RENAME] {os.path.basename(r['path'])} -> (invisible)")
        except OSError as exc:
            failures += 1
            print(f"  [WARN] no se pudo renombrar {os.path.basename(r['path'])}: {exc}")

    if renamed_ok:
        record_post_hashes(backup_dir, renamed_ok)

    shell = None
    pythoncom.CoUninitialize()
    _notify_shell()
    print(f"\n¡Listo! Aplicados: {applied} | Eliminados: {len(dup_deletions)}"
          f" | Renombrados: {renamed} | Sin coincidencia: {len(unmatched)}"
          f" | Fallos: {failures}")
    print(f"Backup: {backup_dir}")
    print("Si los iconos no se actualizaron, presiona F5 en el escritorio.")
    return 1 if failures else 0


# ---------------------------------------------------------------------------
# Organize (former organize_desktop.py) - theme-scoped
# ---------------------------------------------------------------------------
def organize_desktop(cfg, dry_run=False, yes=False):
    win32com, pythoncom = _com()
    keys = set(index_icons(cfg["icons_path"]).keys())
    allowed = [cfg["icons_path"], _published_icons_dir(cfg)]
    pythoncom.CoInitialize()
    shell = win32com.client.Dispatch("WScript.Shell")
    order = [k.replace(" ", "").lower() for k in cfg.get("order", [])]

    items = []
    for desktop in desktop_dirs():
        if not os.path.isdir(desktop):
            continue
        for path in sorted(_shortcuts(desktop)):
            ext = os.path.splitext(path)[1].lower()
            try:
                if ext == ".lnk":
                    raw = shell.CreateShortcut(path).IconLocation
                else:
                    lines = _read_url_lines(path)
                    raw = next((ln.split("=", 1)[1].strip()
                                for ln in lines if ln.lower().startswith("iconfile=")), None)
            except Exception:
                continue
            key = _key_from_icon_path(raw)
            icon_file = _icon_file_from_raw(raw)
            if not key or key.replace(" ", "") not in keys:
                continue
            # Only organize shortcuts whose icon lives in this theme's tree.
            if not icon_file or not is_within(icon_file, allowed):
                continue
            if is_invisible_name(os.path.splitext(os.path.basename(path))[0]):
                continue  # already organized -> keep re-runs idempotent
            items.append({"path": path, "desktop": desktop, "ext": ext,
                          "key": key.replace(" ", "").lower()})

    if not items:
        print("No se encontraron accesos del tema activo.")
        shell = None
        pythoncom.CoUninitialize()
        return 0

    items.sort(key=lambda it: order.index(it["key"]) if it["key"] in order else len(order) + 100)
    print(f"=== Organizador: {cfg['name']} ===  ({len(items)} accesos del tema)")

    used = {}
    for it in items:
        used.setdefault(it["desktop"], set(os.listdir(it["desktop"])))
        it["new_path"] = _unique_invisible_name(it["desktop"], it["ext"], used[it["desktop"]])
        used[it["desktop"]].add(os.path.basename(it["new_path"]))

    if dry_run:
        for i, it in enumerate(items):
            print(f"  [DRY] #{i + 1} {it['key']} -> {os.path.basename(it['new_path'])}")
        shell = None
        pythoncom.CoUninitialize()
        return 0

    if not yes:
        answer = input("¿Reordenar y renombrar estos accesos? [y/N] ").strip().lower()
        if answer not in ("y", "yes", "s", "si", "sí"):
            print("Cancelado.")
            shell = None
            pythoncom.CoUninitialize()
            return 0

    backup_dir = create_backup(cfg, [{"op": "rename", "path": it["path"],
                                      "new_path": it["new_path"]} for it in items])
    failures = 0
    temp = []
    for it in items:
        tmp = os.path.join(it["desktop"], f"__iso_tmp_{uuid.uuid4().hex}{it['ext']}")
        try:
            os.rename(it["path"], tmp)
            it["temp_path"] = tmp
            temp.append(it)
        except OSError as exc:
            failures += 1
            print(f"  [ERROR] {os.path.basename(it['path'])}: {exc}")

    for it in temp:
        try:
            os.rename(it["temp_path"], it["new_path"])
            _notify_file(it["temp_path"])
            _notify_file(it["new_path"])
            print(f"  {it['key']} -> (invisible)")
        except OSError as exc:
            failures += 1
            print(f"  [ERROR] {it['key']}: {exc}")

    shell = None
    pythoncom.CoUninitialize()
    _notify_shell()
    print(f"\n¡Listo! Backup: {backup_dir}")
    if failures:
        print(f"Fallos: {failures}")
    print("Ahora: clic derecho en el escritorio -> 'Ordenar por' -> 'Nombre'.")
    return 1 if failures else 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser(config_path=None):
    p = argparse.ArgumentParser(description="Isoform - motor de iconos unificado")
    p.add_argument("--config", default=config_path, help="Ruta al theme.json")
    p.add_argument("--dry-run", action="store_true", help="No escribe, no refresca, no pregunta")
    p.add_argument("--cleanup", action="store_true", help="Borrar duplicados visibles (opt-in)")
    p.add_argument("--rename", action="store_true", help="Renombrar accesos del tema (opt-in)")
    p.add_argument("--organize", action="store_true", help="Reordenar accesos del tema")
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
    except BackupError as exc:
        print(f"[BACKUP] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run_cli())
