# Graphite Elegance

A premium, minimalist custom icon pack for Windows desktops. Designed to
harmonize with dark modes and clean desktop aesthetics.

**73 icons** — apps, games, tools, and AI.

![Preview](preview.png)

---

## Features

- **Multi-Resolution:** Each `.ico` includes 256, 128, 64, 48, 32, and 16 px renders — no Windows Explorer scaling artifacts.
- **Graphite Squircle:** Dark charcoal background with subtle gradient, drop shadow, and a 1 px inner border.
- **Pure White Silhouettes:** Every logo is thresholded to a clean white mask — no color noise, no gradients on the logo itself.

---

## How to Use — Auto (shared engine)

> **Windows only.** Requires Python 3. Install once: `pip install -r ..\requirements.txt`.

**Option A — one-click launcher**

Double-click `Apply_Theme.ps1` (or `Tools\Install.bat`). This applies the icons
only — it does **not** rename shortcuts.

**Option B — manual (recommended flags)**

```cmd
:: apply icons only (safe default)
python Tools\apply_desktop_icons.py

:: hide shortcut names (opt-in; accessibility caveat) and clean launcher duplicates
python Tools\apply_desktop_icons.py --rename --cleanup

:: preview without changing anything
python Tools\apply_desktop_icons.py --dry-run
```

The engine scans your Desktop (user + public) and applies the matching icon to
every `.lnk` / `.url` it finds. See `../Tools/README.md` for all flags, backups
and `--restore`.

If icons don't update immediately, press **F5** on the Desktop.

---

## How to Use — Manual

1. Right-click any shortcut → **Properties**.
2. Go to the **Shortcut** tab → **Change Icon...**.
3. Browse to `Icons\ICO\` and select the matching file.
4. Click **Apply** → **OK**.

---
*Created by Ayco.*
