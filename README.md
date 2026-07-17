# Isoform — Aesthetic Windows Icon Suites 🌑✨
*Created by [Acourd](https://github.com/Acourd)*

A collection of premium, highly precise, and geometric icon suites designed to bring absolute visual discipline, clean shapes, and minimal contrast to Windows desktops. 

Inspired by the concept of **precision, tactical geometry, and clean borders** (reminiscent of the aesthetic of *ISO* from Valorant), the **Isoform** suite features mathematical squircles (23% border radius) with sharp, solid-white masks and deep vertical gradients.

---

## 🎨 The Icon Suites

Currently, **Isoform** includes 4 unique color palettes designed to fit different desktop themes and wallpaper moods:

| Suite | Aesthetic | Background Gradient | Border / Logo Accent |
| :--- | :--- | :--- | :--- |
| **Graphite Elegance** | Minimalist Dark | #2D2D2D ➔ #0A0A0A | White / Light Shadow |
| **Lumina Frost** | Crisp Light Mode | #FFFFFF ➔ #F5F5F5 | Charcoal / Solid Dark |
| **Midnight Ooo** | Deep Neon/Dark | #1B133A ➔ #0F0A1E | Orange / Neon Pink Border |
| **Horizon Glow** | Warm White/Beige | #FFF8EB ➔ #FFF5E6 | Indigo / Gold Accent Border |

---

## 📂 Repository Structure

Each theme release folder is fully self-contained:
```text
[Theme_Name]_Release/
│
├── Icons/
│   ├── ICO/          ← Multi-resolution Windows .ico (256, 128, 64, 48, 32, 16 px)
│   └── PNG/          ← High-definition transparent assets for docks or Linux
│
├── Tools/
│   └── apply_desktop_icons.py    ← Automator script with custom duplicate cleanup
│
└── Apply_Theme.ps1   ← PowerShell launcher (Right-click ➔ Run with PowerShell)
```

---

## 🚀 Quick Start (Apply Instantly)

### The Automated Way (Recommended)
1. Open the folder of the theme you want to apply (e.g., `Graphite_Elegance_Release`).
2. Right-click **`Apply_Theme.ps1`** and select **"Run with PowerShell"**.
3. The script will automatically scan your desktop (including games and hidden public shortcuts), apply the matching custom icons, rename shortcuts to **invisible names** for a clean aesthetic, and restart Windows Explorer to refresh the cache.

### Anti-Duplication Safeguard
Some game launchers (like Steam, Riot, Epic, or Rockstar) will try to automatically recreate their original visible shortcuts on startup. **Isoform's** applicator includes a detection engine: if it detects a visible shortcut that already has a corresponding invisible, themed counterpart, it will delete the visible duplicate automatically to keep your desktop pristine.

---

## 🛠️ Technical Specifications

*   **Grid Calibration:** Squircles are rendered with a custom mathematical curve to avoid harsh corners, with a bounding box logo fraction calibrated per-resolution (`50%` for 256px down to `68%` for 16px to ensure readability on small scales).
*   **No Scaling Blurs:** Each `.ico` file contains 6 distinct, pre-rendered resolutions (256, 128, 64, 48, 32, 16 px) with 4x supersampling and Lanczos downsampling to prevent Windows from applying ugly real-time resizing filters.
*   **Universal Compatibility:** Works with standard Windows shortcuts (`.lnk`) and Steam Protocol shortcuts (`.url`).

---

## 🔍 Troubleshooting & UAC Limitations

*   **Public Shortcuts (Epic Games, Valorant, Riot, etc.):** If you run the script without administrator privileges, it might not be able to delete or rename shortcuts located in the Public Desktop (`C:\Users\Public\Desktop`) due to Windows UAC permissions. If this happens:
    1.  The script will print a warning but won't crash.
    2.  Simply move those public shortcuts to your personal Desktop folder (`%userprofile%\Desktop`) and run the script again.
*   **Icons don't refresh immediately:** Windows caching is stubborn. If the icons don't change, click on an empty space on your Desktop and press `F5` (or right-click ➔ Refresh). In extreme cases, sign out and sign back in to Windows.
*   **Offline usage:** The script automatically attempts to install `pypiwin32` via `pip` on first run. If you are offline, you can manually install the dependency beforehand with: `pip install pypiwin32 --user`.

*Developed with mathematical rigor and aesthetic passion. © 2026 Acourd.*
