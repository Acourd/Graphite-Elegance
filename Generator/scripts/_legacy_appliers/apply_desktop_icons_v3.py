"""
apply_desktop_icons_v3.py
Aplica iconos Graphite_Elegance al escritorio de Windows y renombra accesos
directos con U+00A0 (Non-Breaking Space) para eliminar etiquetas visibles.

Uso:
    py apply_desktop_icons_v3.py              — aplica iconos + renombra
    py apply_desktop_icons_v3.py --icons      — solo aplica iconos
    py apply_desktop_icons_v3.py --rename     — solo renombra (aplica primero)
    py apply_desktop_icons_v3.py --revert     — restaura nombres originales
    py apply_desktop_icons_v3.py --dry        — muestra plan sin ejecutar
"""
import os
import glob
import sys
import json
import ctypes
import subprocess

try:
    import win32com.client
except ImportError:
    sys.exit("ERROR: pywin32 no instalado.  Ejecuta: pip install pywin32")

# ── Rutas ─────────────────────────────────────────────────────────────────────

ICONS_DIR = r"E:\Shoshin\IA_Proyect\DesktopIcons\1_Themes\Graphite_Elegance_Release\Icons\ICO"
MAP_FILE  = r"E:\Shoshin\IA_Proyect\DesktopIcons\rename_map.json"

# Carácter invisible: Non-Breaking Space (U+00A0).
# El Explorer de Windows lo muestra como etiqueta vacía.
# Se apilan N repeticiones para generar nombres únicos por shortcut.
INVIS = ' '

# ── Mapeo manual (nombre del .lnk en minúsculas → nombre base del .ico) ───────

MANUAL_MAP: dict[str, str] = {
    # Riot / Valorant
    'cliente de riot':        'Riot Client',
    'riot client':            'Riot Client',
    'valorant':               'Valorant',
    'valorant tracker':       'Valorant Tracker',
    'blitz':                  'Blitz',
    # NVIDIA
    'nvidia app':             'Nvidia App',
    'nvidia':                 'Nvidia App',
    # Grabación / Clips
    'medal':                  'Medal',
    'obs studio':             'Obs',
    'obs':                    'Obs',
    # Epic Games
    'epic games launcher':    'Epic Games',
    'epicgameslauncher':      'Epic Games',
    'epic games':             'Epic Games',
    # Microsoft
    'microsoft edge':         'Edge',
    'edge':                   'Edge',
    'word':                   'Word',
    'excel':                  'Excel',
    'powerpoint':             'Powerpoint',
    'outlook':                'Outlook',
    'teams':                  'Teams',
    # Google
    'chrome':                 'Chrome',
    'google chrome':          'Chrome',
    'gmail':                  'Gmail',
    'classroom':              'Classroom',
    'notebooklm':             'NotebookLM',
    'ai studio':              'AI Studio',
    # Redes sociales / Productividad
    'discord':                'Discord',
    'spotify':                'Spotify',
    'reddit':                 'Reddit',
    'linkedin':               'Linkedin',
    'pinterest':              'Pinterest',
    'youtube':                'Youtube',
    'github':                 'Github',
    'perplexity':             'Perplexity',
    'canva':                  'Canva',
    'notion':                 'Notion',
    # IA
    'claude':                 'Claude Ai',
    'claude ai':              'Claude Ai',
    'chatgpt':                'Chatgpt',
    'gemini':                 'Gemini',
    # Juegos
    'steam':                  'Steam',
    'terraria':               'Terraria',
    'tmodloader':             'tModLoader',
    'minecraft':              'Minecraft',
    'atlauncher':             'ATLauncher',
    'roblox':                 'Roblox',
    'aimlabs':                'Aimlabs',
    'hytale':                 'Hytale',
    # Utilidades
    'lossless scaling':       'Lossless Scaling',
    'lossless-scaling':       'Lossless Scaling',
    'mem reduct':             'Mem Reduct',
    'mini cozy room':         'Mini Cozy Room',
    'minicozyroom':           'Mini Cozy Room',
    'wallpaper engine':       'Wallpaper Engine',
    'msi afterburner':        'MSI Afterburner',
    'ccleaner':               'Ccleaner',
    'geek uninstaller':       'Geek Uninstaller',
    'geek-uninstaller':       'Geek Uninstaller',
    'helium':                 'Helium',
    'antigravity':            'Antigravity',
    "kovaak's":               'Kovacks',
    'kovaaks':                'Kovacks',
    'vscode':                 'Vscode',
    'visual studio code':     'Vscode',
    'process lasso':          'Process Lasso',
    'labymod':                'Labymod',
    'optimizer':              'Optimizer',
}


# ── Helpers internos ──────────────────────────────────────────────────────────

def _desktops() -> list[str]:
    """Devuelve escritorios de Usuario y Público que existan."""
    paths = [os.path.join(os.environ['USERPROFILE'], 'Desktop')]
    pub = os.environ.get('PUBLIC', r'C:\Users\Public')
    paths.append(os.path.join(pub, 'Desktop'))
    return [p for p in paths if os.path.exists(p)]


def _load_icons() -> dict[str, str]:
    """Carga todos los .ico en ICO_DIR: clave = stem normalizado → ruta."""
    result: dict[str, str] = {}
    for f in os.listdir(ICONS_DIR):
        if not f.lower().endswith('.ico'):
            continue
        stem = os.path.splitext(f)[0]
        full = os.path.join(ICONS_DIR, f)
        result[stem.lower()] = full
        result[stem.lower().replace(' ', '')] = full
    return result


def _find_icon(stem: str, icons: dict[str, str]) -> str | None:
    """Resuelve qué ICO corresponde a un stem de shortcut.
    Orden: mapa manual → exacto normalizado → parcial."""
    key = stem.lower().strip()
    # 1. Mapa manual
    mapped = MANUAL_MAP.get(key)
    if mapped and mapped.lower() in icons:
        return icons[mapped.lower()]
    # 2. Exacto (con y sin espacios)
    if key in icons:
        return icons[key]
    no_sp = key.replace(' ', '')
    if no_sp in icons:
        return icons[no_sp]
    # 3. Parcial (el stem contiene o está contenido en el nombre del ICO)
    for iname, ipath in icons.items():
        if len(key) >= 4 and (iname in key or key in iname):
            return ipath
    return None


def _is_invisible(name: str) -> bool:
    """True si el stem del archivo es solo caracteres U+00A0."""
    return bool(name) and all(c == INVIS for c in name)


def _load_map() -> dict[str, str]:
    if os.path.exists(MAP_FILE):
        with open(MAP_FILE, encoding='utf-8') as f:
            return json.load(f)
    return {}


def _save_map(data: dict[str, str]) -> None:
    os.makedirs(os.path.dirname(MAP_FILE), exist_ok=True)
    with open(MAP_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _original_stem_from_map(invis_stem: str) -> str | None:
    """Busca en rename_map el nombre original de un shortcut invisible."""
    rmap = _load_map()
    for invis_key, original in rmap.items():
        if invis_key == invis_stem:
            return os.path.splitext(original)[0]
    return None


def _patch_url(path: str, ico_path: str) -> None:
    """Inyecta/sobreescribe IconFile= en un archivo .url (formato INI)."""
    with open(path, encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    has_file = has_idx = False
    for i, line in enumerate(lines):
        ll = line.lower()
        if ll.startswith('iconfile='):
            lines[i] = f'IconFile={ico_path}\n'
            has_file = True
        elif ll.startswith('iconindex='):
            lines[i] = 'IconIndex=0\n'
            has_idx = True
    if not has_file:
        for i, line in enumerate(lines):
            if line.strip().lower() == '[internetshortcut]':
                ins = i + 1
                lines.insert(ins, f'IconFile={ico_path}\n')
                if not has_idx:
                    lines.insert(ins + 1, 'IconIndex=0\n')
                break
    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(lines)


def _refresh_desktop() -> None:
    """Notifica al shell que actualice los iconos del escritorio."""
    try:
        SHCNE_ASSOCCHANGED = 0x08000000
        SHCNF_IDLIST = 0x0000
        ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)
    except Exception:
        pass
    # Refresco adicional vía ie4uinit (funciona en Win 10/11)
    try:
        subprocess.run(['ie4uinit.exe', '-show'], capture_output=True, timeout=5)
    except Exception:
        pass


# ── Funciones principales ─────────────────────────────────────────────────────

def apply_icons(dry_run: bool = False) -> int:
    """
    Aplica iconos Graphite_Elegance a todos los shortcuts del escritorio.
    Si un shortcut ya fue renombrado como invisible, usa el mapa guardado
    para seguir encontrando el ICO correcto.
    Devuelve el número de shortcuts actualizados.
    """
    icons = _load_icons()
    shell = win32com.client.Dispatch('WScript.Shell')
    count = 0

    for desktop in _desktops():
        files = (glob.glob(os.path.join(desktop, '*.lnk')) +
                 glob.glob(os.path.join(desktop, '*.url')))
        for fpath in files:
            basename = os.path.basename(fpath)
            stem, ext = os.path.splitext(basename)

            # Si ya fue renombrado, recuperar nombre original del mapa
            effective_stem = stem
            if _is_invisible(stem):
                original = _original_stem_from_map(stem)
                if original:
                    effective_stem = original
                else:
                    print(f'[SKIP] Invisible sin mapa: {fpath}')
                    continue

            ico = _find_icon(effective_stem, icons)
            if not ico:
                print(f'[SKIP] Sin ICO para: "{effective_stem}"')
                continue

            ico_basename = os.path.basename(ico)
            try:
                if dry_run:
                    print(f'[DRY ] "{effective_stem}" → {ico_basename}')
                    count += 1
                    continue

                if ext.lower() == '.lnk':
                    sc = shell.CreateShortcut(fpath)
                    new_loc = f'{ico}, 0'
                    if sc.IconLocation != new_loc:
                        sc.IconLocation = new_loc
                        sc.Save()
                        print(f'[OK ] "{effective_stem}" → {ico_basename}')
                        count += 1
                    else:
                        print(f'[   ] Sin cambio: "{effective_stem}"')

                elif ext.lower() == '.url':
                    _patch_url(fpath, ico)
                    print(f'[OK ] "{effective_stem}" → {ico_basename}')
                    count += 1

            except Exception as e:
                print(f'[ERR] "{effective_stem}": {e}')

    if not dry_run:
        _refresh_desktop()

    print(f'\nIconos aplicados: {count}')
    return count


def rename_invisible(dry_run: bool = False) -> int:
    """
    Renombra todos los shortcuts del escritorio a nombres invisibles (U+00A0 × N).
    Guarda el mapa {stem_invisible: nombre_original} en rename_map.json.
    Devuelve el número de shortcuts renombrados.
    """
    rmap = _load_map()
    counter = len(rmap) + 1  # Continúa desde donde se quedó si ya hay renombrados
    count = 0

    for desktop in _desktops():
        files = (glob.glob(os.path.join(desktop, '*.lnk')) +
                 glob.glob(os.path.join(desktop, '*.url')))
        for fpath in files:
            basename = os.path.basename(fpath)
            stem, ext = os.path.splitext(basename)

            if _is_invisible(stem):
                print(f'[SKIP] Ya invisible: #{list(rmap.keys()).index(stem) + 1 if stem in rmap else "?"}')
                continue

            new_stem = INVIS * counter
            new_path = os.path.join(os.path.dirname(fpath), new_stem + ext)

            if dry_run:
                print(f'[DRY ] "{stem}" → invisible #{counter}')
                counter += 1
                count += 1
                continue

            try:
                os.rename(fpath, new_path)
                rmap[new_stem] = basename  # guarda nombre original completo
                print(f'[OK ] "{stem}" → invisible #{counter}')
                counter += 1
                count += 1
            except Exception as e:
                print(f'[ERR] "{stem}": {e}')

    if not dry_run and count:
        _save_map(rmap)
        print(f'\nMapa guardado en: {MAP_FILE}')
        _refresh_desktop()

    print(f'Shortcuts renombrados: {count}')
    return count


def revert_rename(dry_run: bool = False) -> int:
    """
    Restaura los nombres originales usando rename_map.json.
    Devuelve el número de shortcuts restaurados.
    """
    rmap = _load_map()
    if not rmap:
        print('rename_map.json vacío o inexistente. Nada que revertir.')
        return 0

    count = 0
    for desktop in _desktops():
        files = (glob.glob(os.path.join(desktop, '*.lnk')) +
                 glob.glob(os.path.join(desktop, '*.url')))
        for fpath in files:
            stem = os.path.splitext(os.path.basename(fpath))[0]
            if not _is_invisible(stem):
                continue
            original_basename = rmap.get(stem)
            if not original_basename:
                continue
            original_path = os.path.join(os.path.dirname(fpath), original_basename)

            if dry_run:
                print(f'[DRY ] Invisible → "{original_basename}"')
                count += 1
                continue
            try:
                os.rename(fpath, original_path)
                print(f'[OK ] Restaurado: "{original_basename}"')
                count += 1
            except Exception as e:
                print(f'[ERR] {e}')

    if not dry_run and count:
        _refresh_desktop()

    print(f'Shortcuts restaurados: {count}')
    return count


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    args = set(sys.argv[1:])
    dry  = '--dry'    in args
    only_icons  = '--icons'  in args
    only_rename = '--rename' in args
    do_revert   = '--revert' in args

    if dry:
        print('=== MODO DRY-RUN - sin cambios reales ===\n')

    if do_revert:
        revert_rename(dry_run=dry)
        return

    if only_icons:
        apply_icons(dry_run=dry)
        return

    if only_rename:
        print('--- Paso 1: Aplicar iconos (necesario antes de renombrar) ---')
        apply_icons(dry_run=dry)
        print('\n--- Paso 2: Renombrar con caracter invisible ---')
        rename_invisible(dry_run=dry)
        return

    # Sin flags: flujo completo
    print('--- Paso 1: Aplicar iconos ---')
    apply_icons(dry_run=dry)
    print('\n--- Paso 2: Renombrar con caracter invisible ---')
    rename_invisible(dry_run=dry)


if __name__ == '__main__':
    main()
