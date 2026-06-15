"""
Graphite Elegance — Icon Applicator
Scans your Desktop shortcuts (.lnk / .url) and applies matching icons automatically.

Windows only.
Requirements:  pip install pypiwin32   (or run Tools\Install.bat)
Usage:         python Tools\apply_desktop_icons.py
"""
import sys

if sys.platform != "win32":
    print("Error: Graphite Elegance is designed for Windows only.")
    raise SystemExit(1)

import os
import glob
import ctypes
import pythoncom

try:
    import win32com.client
except ImportError:
    print("Error: pypiwin32 is not installed.")
    print("       Run:  pip install pypiwin32")
    print("       Or double-click:  Tools\\Install.bat")
    raise SystemExit(1)

# SHChangeNotify constants
_SHCNE_UPDATEITEM   = 0x00002000   # notify Explorer that a specific file changed
_SHCNE_ASSOCCHANGED = 0x08000000   # global flush at the end
_SHCNF_PATH         = 0x0001
_SHCNF_FLUSHNOWAIT  = 0x1000
_SHCNF_IDLIST       = 0x0000


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


def apply_icons_to_desktop():
    pythoncom.CoInitialize()

    desktops = [
        os.path.join(os.environ["USERPROFILE"], "Desktop"),
        os.path.join(os.environ.get("PUBLIC", r"C:\Users\Public"), "Desktop"),
    ]

    _script_dir = os.path.dirname(os.path.abspath(__file__))
    icons_dir   = os.path.normpath(os.path.join(_script_dir, "..", "Icons", "ICO"))

    if not os.path.exists(icons_dir):
        print(f"[ERROR] Icons folder not found: {icons_dir}")
        print("        Make sure the folder structure is intact (Icons\\ICO\\ next to Tools\\).")
        pythoncom.CoUninitialize()
        return

    # Build name → path lookup (flat folder for Graphite)
    available_icons = {}
    for fname in os.listdir(icons_dir):
        if fname.lower().endswith(".ico"):
            key = os.path.splitext(fname)[0].lower()
            full = os.path.join(icons_dir, fname)
            available_icons[key]                  = full
            available_icons[key.replace(" ", "")] = full

    shell = win32com.client.Dispatch("WScript.Shell")
    applied   = 0
    unmatched = []

    for desktop in desktops:
        if not os.path.isdir(desktop):
            continue

        shortcuts = (glob.glob(os.path.join(desktop, "*.lnk")) +
                     glob.glob(os.path.join(desktop, "*.url")))

        for path in shortcuts:
            name = os.path.splitext(os.path.basename(path))[0].lower()

            icon_path = available_icons.get(name)
            if not icon_path:
                for key, val in available_icons.items():
                    if key in name or name in key:
                        icon_path = val
                        break

            if not icon_path:
                unmatched.append(os.path.basename(path))
                continue

            ext = os.path.splitext(path)[1].lower()
            try:
                if ext == ".lnk":
                    sc  = shell.CreateShortcut(path)
                    loc = f"{icon_path}, 0"
                    if sc.IconLocation != loc:
                        sc.IconLocation = loc
                        sc.Save()
                        _notify_file(path)
                        print(f"  [OK] {os.path.basename(path)}  →  {os.path.basename(icon_path)}")
                        applied += 1

                elif ext == ".url":
                    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                        lines = fh.readlines()

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
                    print(f"  [OK] {os.path.basename(path)}  →  {os.path.basename(icon_path)}")
                    applied += 1

            except Exception as exc:
                print(f"  [FAIL] {os.path.basename(path)}: {exc}")

    _notify_shell()
    pythoncom.CoUninitialize()

    print(f"\nDone!  Applied: {applied}  |  No match: {len(unmatched)}")

    if unmatched:
        print("\nShortcuts without a matching icon:")
        for n in sorted(set(unmatched)):
            print(f"  - {n}")

    print("\nIf icons haven't updated yet, press F5 on the desktop.")


if __name__ == "__main__":
    apply_icons_to_desktop()
