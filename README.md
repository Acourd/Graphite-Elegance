# Desktop Icon Pack — Windows

Two companion themes for Windows desktops. Both share the same squircle base shape and visual pipeline; they differ in color scheme (and a couple of icons).

| Theme | Style | Icons |
|-------|-------|-------|
| **Graphite Elegance** | Dark charcoal background · white silhouette logos | 56 |
| **Lumina Frost** | Bright white background · dark silhouette logos | 54 |

---

## Themes

### Graphite Elegance
Dark squircle with a subtle top-to-bottom gradient (#2D2D2D → #0A0A0A), 1 px inner border, and a dual drop shadow under each logo. Designed for dark-mode setups and clean desktop aesthetics.

![Graphite Elegance preview](Graphite_Elegance_Release/preview.png)

→ [Graphite\_Elegance\_Release/](Graphite_Elegance_Release/)

### Lumina Frost
Inverted companion: bright white squircle (#FFFFFF → #F5F5F5) with a dark logo (#191919). No border or shadow — the contrast does the work. Designed for light-mode or minimal setups.

![Lumina Frost preview](Lumina_Frost_Release/preview.png)

→ [Lumina\_Frost\_Release/](Lumina_Frost_Release/)

---

## What's included

Each theme folder contains:

```
Icons/
  ICO/          ← multi-resolution .ico files (256 · 128 · 64 · 48 · 32 · 16 px)
Tools/
  apply_desktop_icons.py    ← auto-applies icons to Desktop shortcuts
  Install.ps1               ← installs the Python dependency + runs the script
README.md
```

---

## Quick start

**One-click (recommended)**
Right-click `Tools\Install.ps1` inside either theme folder → **Run with PowerShell**.
The script installs the required dependency and applies icons automatically.

**Manual**
```cmd
pip install pypiwin32
python Tools\apply_desktop_icons.py
```

The script scans your Desktop (user + public) and applies the matching icon to every `.lnk` and `.url` shortcut it finds. Unmatched shortcuts are listed at the end.

> **Windows only.** Requires Python 3 installed on your system.

---

## Icon list

<details>
<summary>Graphite Elegance — 56 icons</summary>

AI Studio · Aimlabs · Antigravity · ATLauncher · Blitz · Canva · Ccleaner · Chatgpt · Chrome · Classroom · Claude Ai · Discord · Edge · Epic Games · Excel · Geek Uninstaller · Gemini · Github · Gmail · Go · Helium · Images · Iso · Kindle · Kovacks · Labymod · Linkedin · Lossless Scaling · Medal · Mem Reduct · Minecraft · Minecraft V2 · Mini Cozy Room · Msiafterburner · NotebookLM · Nvidia App · Obs · Olympus · Opendesign · Perplexity · Pinterest · Powerpoint · Process Lasso · Reddit · Riot Client · Roblox · Spotify · Steam · Terraria · tModLoader · Valorant · Valorant Tracker · Vscode · Wallpaper Engine · Word · Youtube Music

</details>

<details>
<summary>Lumina Frost — 54 icons</summary>

AI Studio · Aimlabs · Antigravity · ATLauncher · Blitz · Canva · Ccleaner · Chatgpt · Chrome · Classroom · Claude Ai · Discord · Edge · Epic Games · Excel · Geek Uninstaller · Gemini · Github · Go · Helium · Images · Iso · Kindle · Kovacks · Labymod · Linkedin · Lossless Scaling · Medal · Mem Reduct · Minecraft · Minecraft V2 · Mini Cozy Room · Msiafterburner · NotebookLM · Nvidia App · Obs · Olympus · Opendesign · Pinterest · Powerpoint · Process Lasso · Reddit · Riot Client · Roblox · Spotify · Steam · Terraria · tModLoader · Valorant · Valorant Tracker · Vscode · Wallpaper Engine · Word · Youtube Music

</details>

---

## Technical specs

- **Format:** `.ico` with 6 embedded resolutions — 256, 128, 64, 48, 32, 16 px
- **Rendering:** 4× supersampling → LANCZOS downsample
- **Shape:** squircle with `border-radius ≈ 23%` of icon size
- **Source:** each logo is extracted as a binary silhouette via CIELab or alpha-channel analysis

---

*Created by Ayco.*
