# White Space Pixel

An OMORI-inspired pixel-art icon pack for Windows desktops. Monochrome, minimal
and deliberately lo-fi.

**69 icons** — apps, games, tools, and AI.

---

## Features

- **Multi-Resolution:** Each `.ico` includes 256, 128, 64, 48, 32, and 16 px renders.
- **Pixel aesthetic:** nearest-neighbour style silhouettes on a flat base.
- **Monochrome White Space palette.**

---

## How to Use — Auto (shared engine)

> **Windows only.** Requires Python 3. Install once: `pip install -r ..\requirements.txt`.

```cmd
:: apply icons only (safe default), from this theme folder
python ..\Tools\icon_engine.py --config theme.json

:: hide shortcut names (opt-in) and clean launcher duplicates
python ..\Tools\icon_engine.py --config theme.json --rename --cleanup

:: preview without changing anything
python ..\Tools\icon_engine.py --config theme.json --dry-run
```

Or double-click `Tools\Install.bat` (applies icons only). If icons don't update
immediately, press **F5** on the Desktop. See `../Tools/README.md` for all flags,
backups and `--restore`.

---

## How to Use — Manual

1. Right-click any shortcut → **Properties**.
2. Go to the **Shortcut** tab → **Change Icon...**.
3. Browse to `Icons\ICO\` and select the matching file.
4. Click **Apply** → **OK**.

---
*Created by Ayco.*
