"""
Graphite Elegance - Desktop Icons Organizer
Renumbers the invisible desktop shortcut names (\u00a0) to force a clean, 3-column sorted layout.
Usage: Run with Python/Py launcher, then right-click on the desktop and select "Sort by" -> "Name".
"""
import os
import sys
import ctypes
import subprocess

try:
    import win32com.client
    import pythoncom
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pypiwin32", "--quiet"])
    import win32com.client
    import pythoncom

# SHChangeNotify constants
_SHCNE_UPDATEITEM   = 0x00002000
_SHCNE_ASSOCCHANGED = 0x08000000
_SHCNF_PATH         = 0x0001
_SHCNF_FLUSHNOWAIT  = 0x1000
_SHCNF_IDLIST       = 0x0000

def _notify_file(path):
    ctypes.windll.shell32.SHChangeNotify(
        _SHCNE_UPDATEITEM,
        _SHCNF_PATH | _SHCNF_FLUSHNOWAIT,
        ctypes.c_wchar_p(path),
        None,
    )

def _notify_shell():
    ctypes.windll.shell32.SHChangeNotify(_SHCNE_ASSOCCHANGED, _SHCNF_IDLIST, None, None)

def _key_from_icon_path(raw):
    if not raw:
        return None
    candidate = raw.split(",")[0].strip().strip('"')
    if not candidate.lower().endswith(".ico"):
        return None
    return os.path.splitext(os.path.basename(candidate))[0].lower()

def _read_url_lines(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        return fh.readlines()

# Criterio de ordenación recomendado (Alternativa 1 - 3 Columnas de arriba a abajo)
ORDERED_KEYS = [
    # Columna 1: Productividad, Comunicación y Sistema
    "antigravity",
    "discord",
    "chrome",
    "jan",
    "excel",
    "word",
    "powerpoint",
    "images",
    "classroom",

    # Columna 2: Plataformas y Juegos
    "steam",
    "riotclient",
    "epicgames",
    "rockstargameslauncher",
    "rockstargames",
    "atlauncher",
    "valorant",
    "valoranttracker",
    "leagueoflegends",
    "repo",
    "stick",

    # Columna 3: Herramientas del Sistema y Hardware
    "nvidiaapp",
    "nvidiabroadcast",
    "ccleaner",
    "memreduct",
    "geekuninstaller",
    "obs",
    "medal"
]

def organize():
    pythoncom.CoInitialize()
    shell = win32com.client.Dispatch("WScript.Shell")

    desktops = [
        os.path.join(os.environ["USERPROFILE"], "Desktop"),
        os.path.join(os.environ.get("PUBLIC", r"C:\Users\Public"), "Desktop"),
    ]

    print("=== Organizador de Escritorio (Graphite Elegance) ===")
    
    # 1. Escanear todos los accesos directos que tengan iconos aplicados
    shortcuts_to_order = []
    
    for desktop in desktops:
        if not os.path.isdir(desktop):
            continue
            
        import glob
        files = glob.glob(os.path.join(desktop, "*.lnk")) + glob.glob(os.path.join(desktop, "*.url"))
        
        for path in files:
            ext = os.path.splitext(path)[1].lower()
            icon_key = None
            
            try:
                if ext == ".lnk":
                    sc = shell.CreateShortcut(path)
                    icon_key = _key_from_icon_path(sc.IconLocation)
                elif ext == ".url":
                    lines = _read_url_lines(path)
                    current_icon = next((l.split("=", 1)[1].strip() for l in lines if l.lower().startswith("iconfile=")), None)
                    icon_key = _key_from_icon_path(current_icon)
            except Exception as e:
                continue
                
            if icon_key:
                # Almacenar la clave normalizada
                norm_key = icon_key.replace(" ", "").lower()
                shortcuts_to_order.append({
                    "path": path,
                    "desktop": desktop,
                    "ext": ext,
                    "key": norm_key
                })

    if not shortcuts_to_order:
        print("No se encontraron accesos directos con iconos del pack aplicados.")
        pythoncom.CoUninitialize()
        return

    # 2. Ordenar los accesos directos según la lista ORDERED_KEYS
    def sort_index(item):
        k = item["key"]
        if k in ORDERED_KEYS:
            return ORDERED_KEYS.index(k)
        # Si no está en la lista de ordenación, colocar al final
        return len(ORDERED_KEYS) + 100

    shortcuts_to_order.sort(key=sort_index)

    print(f"\nOrdenando {len(shortcuts_to_order)} accesos directos...")

    # 3. Renombrado en Dos Fases para evitar colisiones de archivos
    # Fase 1: renombrar temporalmente a nombres únicos
    temp_renamed = []
    for idx, item in enumerate(shortcuts_to_order):
        temp_name = os.path.join(item["desktop"], f"__temp_{idx}_{item['key']}{item['ext']}")
        try:
            os.rename(item["path"], temp_name)
            _notify_file(item["path"])
            _notify_file(temp_name)
            item["temp_path"] = temp_name
            temp_renamed.append(item)
        except Exception as e:
            print(f"  [ERROR] No se pudo renombrar temporalmente {os.path.basename(item['path'])}: {e}")

    # Fase 2: asignar la cantidad exacta de espacios invisibles (\u00a0)
    for idx, item in enumerate(temp_renamed):
        spaces_count = idx + 1
        new_name = "\u00a0" * spaces_count
        final_path = os.path.join(item["desktop"], f"{new_name}{item['ext']}")
        
        try:
            os.rename(item["temp_path"], final_path)
            _notify_file(item["temp_path"])
            _notify_file(final_path)
            print(f"  [#{spaces_count}] {item['key']}  ->  (Invisible)")
        except Exception as e:
            print(f"  [ERROR] No se pudo asignar nombre invisible final para {item['key']}: {e}")

    _notify_shell()
    shell = None
    pythoncom.CoUninitialize()
    
    print("\n¡Listo! Todos los accesos directos del pack han sido reordenados alfabéticamente.")
    print(">> AHORA: Haz clic derecho en tu escritorio, ve a 'Ordenar por' y selecciona 'Nombre'.")

if __name__ == "__main__":
    organize()
