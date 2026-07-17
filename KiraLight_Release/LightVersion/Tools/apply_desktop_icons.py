"""
Kira Light (Light Version) - Icon Applicator
Scans your Desktop shortcuts (.lnk / .url) and applies matching icons automatically.
Windows only.
"""
import sys
import os
import subprocess

# Auto-install dependencies if missing
try:
    import win32com.client
    import pythoncom
except ImportError:
    print("Instalando dependencias requeridas (pypiwin32)...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pypiwin32", "--quiet"])
        import win32com.client
        import pythoncom
        print("Dependencias instaladas con éxito.\n")
    except Exception as e:
        print(f"Error al instalar pypiwin32 automáticamente: {e}")
        print("Por favor, ejecuta en una consola con permisos de administrador: pip install pypiwin32")
        input("\nPresiona Enter para salir...")
        sys.exit(1)

import glob
import ctypes

if sys.platform != "win32":
    print("Error: Este script está diseñado para Windows únicamente.")
    raise SystemExit(1)

# SHChangeNotify constants
_SHCNE_UPDATEITEM   = 0x00002000   # notify Explorer that a specific file changed
_SHCNE_ASSOCCHANGED = 0x08000000   # global flush at the end
_SHCNF_PATH         = 0x0001
_SHCNF_FLUSHNOWAIT  = 0x1000
_SHCNF_IDLIST       = 0x0000

# Steam AppID to Icon key mapping
STEAM_APP_MAP = {
    "824270": "kovacks",
    "993090": "lossless scaling",
    "105600": "terraria",
    "431960": "wallpaper engine",
    "1281930": "tmodloader",
    "1460040": "mini cozy room"
}

def _notify_file(path):
    """Tell Explorer to reload the icon for one specific shortcut."""
    ctypes.windll.shell32.SHChangeNotify(
        _SHCNE_UPDATEITEM,
        _SHCNF_PATH | _SHCNF_FLUSHNOWAIT,
        ctypes.c_wchar_p(path),
        None,
    )

def _notify_shell():
    """Global icon-cache flush after all changes are done."""
    ctypes.windll.shell32.SHChangeNotify(_SHCNE_ASSOCCHANGED, _SHCNF_IDLIST, None, None)

def _key_from_icon_path(raw):
    """'C:\\...\\Discord.ico,0' -> 'discord'  (None if not an .ico path)."""
    if not raw:
        return None
    candidate = raw.split(",")[0].strip().strip('"')
    if not candidate.lower().endswith(".ico"):
        return None
    return os.path.splitext(os.path.basename(candidate))[0].lower()

def _lookup(key, available):
    """Exact then space-insensitive lookup."""
    if not key:
        return None
    key = key.lower()
    if key in available:
        return available[key]
    nk = key.replace(" ", "")
    if nk in available:
        return available[nk]
    return None

def _resolve_lnk(sc, shortcut_path, available):
    # 1. Icon already assigned
    hit = _lookup(_key_from_icon_path(sc.IconLocation), available)
    if hit:
        return hit
    # 2. Shortcut file name
    name = os.path.splitext(os.path.basename(shortcut_path))[0]
    hit = _lookup(name, available)
    if hit:
        return hit
    # 3. Target path segments (folder names + exe name), longest first
    target = (sc.TargetPath or "").replace("/", "\\")
    segs = {os.path.splitext(s)[0].lower() for s in target.split("\\") if s}
    for seg in sorted(segs, key=len, reverse=True):
        hit = _lookup(seg, available)
        if hit:
            return hit
    return None

def _read_url_lines(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        return fh.readlines()

def _resolve_url(lines, shortcut_path, available):
    # 1. Steam URL AppID mapping (High priority to avoid Steam shortcut desync)
    for line in lines:
        if line.lower().startswith("url="):
            url_val = line.split("=", 1)[1].strip()
            if url_val.lower().startswith("steam://rungameid/"):
                appid = url_val.lower().split("steam://rungameid/")[1].strip()
                appid_clean = "".join(c for c in appid if c.isdigit())
                if appid_clean in STEAM_APP_MAP:
                    hit = _lookup(STEAM_APP_MAP[appid_clean], available)
                    if hit:
                        return hit
    # 2. Icon already assigned (IconFile=)
    for line in lines:
        if line.lower().startswith("iconfile="):
            hit = _lookup(_key_from_icon_path(line.split("=", 1)[1].strip()), available)
            if hit:
                return hit
    # 3. Shortcut file name
    name = os.path.splitext(os.path.basename(shortcut_path))[0]
    return _lookup(name, available)

def apply_icons_to_desktop():
    pythoncom.CoInitialize()

    desktops = [
        os.path.join(os.environ["USERPROFILE"], "Desktop"),
        os.path.join(os.environ.get("PUBLIC", r"C:\Users\Public"), "Desktop"),
    ]

    _script_dir = os.path.dirname(os.path.abspath(__file__))
    icons_dir   = os.path.normpath(os.path.join(_script_dir, "..", "Icons", "ICO"))

    if not os.path.exists(icons_dir):
        print(f"[ERROR] No se encontró la carpeta de iconos: {icons_dir}")
        pythoncom.CoUninitialize()
        return

    # Copiar a ruta persistente en Local AppData para evitar enlaces rotos si se mueve la carpeta de instalación
    import shutil
    appdata_local = os.environ.get("LOCALAPPDATA", os.path.join(os.environ["USERPROFILE"], "AppData", "Local"))
    persist_dir = os.path.join(appdata_local, "Icons_Engine", "Themes", "KiraLight_Light")
    persist_icons_dir = os.path.join(persist_dir, "Icons")

    try:
        if os.path.exists(persist_icons_dir):
            shutil.rmtree(persist_icons_dir)
        shutil.copytree(icons_dir, persist_icons_dir)
        print(f"  [INFO] Iconos copiados a ubicación persistente: {persist_icons_dir}")
        icons_dir = persist_icons_dir
    except Exception as e:
        print(f"  [WARN] No se pudo copiar a la carpeta persistente ({e}). Se usarán los iconos locales.")

    # name -> path lookup across all subfolders (recursive scan to support categories)
    available_icons = {}
    for root, _dirs, files in os.walk(icons_dir):
        for fname in files:
            if fname.lower().endswith(".ico"):
                key = os.path.splitext(fname)[0].lower()
                full = os.path.join(root, fname)
                available_icons[key]                  = full
                available_icons[key.replace(" ", "")] = full

    shell = win32com.client.Dispatch("WScript.Shell")
    applied   = 0
    unchanged = 0
    unmatched = []

    for desktop in desktops:
        if not os.path.isdir(desktop):
            continue

        shortcuts = (glob.glob(os.path.join(desktop, "*.lnk")) +
                     glob.glob(os.path.join(desktop, "*.url")))

        for path in shortcuts:
            ext = os.path.splitext(path)[1].lower()
            try:
                if ext == ".lnk":
                    sc = shell.CreateShortcut(path)
                    icon_path = _resolve_lnk(sc, path, available_icons)
                    label = os.path.splitext(os.path.basename(sc.TargetPath or path))[0]
                    if not icon_path:
                        unmatched.append(label)
                        continue
                    loc = f"{icon_path}, 0"
                    if sc.IconLocation != loc:
                        sc.IconLocation = loc
                        sc.Save()
                        _notify_file(path)
                        print(f"  [OK] {label}  ->  {os.path.basename(icon_path)}")
                        applied += 1
                    else:
                        unchanged += 1

                elif ext == ".url":
                    lines = _read_url_lines(path)
                    icon_path = _resolve_url(lines, path, available_icons)
                    url_line = next((l.strip()[4:] for l in lines if l.lower().startswith("url=")), "")
                    label = url_line or os.path.basename(path)
                    if not icon_path:
                        unmatched.append(label)
                        continue

                    current = next((l.split("=", 1)[1].strip()
                                    for l in lines if l.lower().startswith("iconfile=")), None)
                    if current == icon_path:
                        unchanged += 1
                        continue

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
                    print(f"  [OK] {label}  ->  {os.path.basename(icon_path)}")
                    applied += 1

            except Exception as exc:
                print(f"  [FAIL] {os.path.basename(path)}: {exc}")

    _notify_shell()
    shell = None
    pythoncom.CoUninitialize()

    print(f"\n¡Listo!  Aplicados: {applied}  |  Ya correctos: {unchanged}  |  Sin coincidencia: {len(unmatched)}")

    if unmatched:
        print("\nAccesos directos sin icono coincidente:")
        for n in sorted(set(unmatched)):
            print(f"  - {n}")

    print("\nSi los iconos no se han actualizado, presiona F5 en el escritorio.")


if __name__ == "__main__":
    apply_icons_to_desktop()
