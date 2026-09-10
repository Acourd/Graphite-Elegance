# Isoform — Aesthetic Windows Icon Suites 🌑✨
*Created by [Acourd](https://github.com/Acourd)*

A collection of premium, minimalist, and geometric icon suites for Windows desktops.

| Theme | Icons | Notes |
|---|---:|---|
| Graphite Elegance | 73 | dark squircle, white silhouettes |
| Lumina Frost | 71 | light squircle, dark silhouettes |
| Midnight Ooo | — | deep night palette |
| Horizon Glow | — | warm gradient palette |
| White Space Pixel | 69 | pixel-art variant |
| KiraLight (Dark / Light) | 138 | 2 × 69 |

---

## 🎨 Theme Previews

<details><summary>Graphite Elegance</summary><br>

![Graphite Elegance Preview](Graphite_Elegance_Release/preview.png)
</details>

<details><summary>Lumina Frost</summary><br>

![Lumina Frost Preview](Lumina_Frost_Release/preview.png)
</details>

<details><summary>Midnight Ooo</summary><br>

![Midnight Ooo Preview](Ooo_Release/preview_midnight.png)
</details>

<details><summary>Horizon Glow</summary><br>

![Horizon Glow Preview](Ooo_Release/preview_horizon.png)
</details>

---

## 📂 Repository Structure

```text
.
├── Generator/                    ← icon factory (scripts + raw assets)
│   ├── scripts/                  ← silhouette → compose → PNG → .ico
│   └── assets/Raw_Silhouettes/   ← source logos
│
├── Tools/                        ← shared engine
│   ├── icon_engine.py            ← one applicator + organizer for every theme
│   └── icon_validate.py          ← icon resolution/name gate (used by CI)
│
└── [Theme]_Release/
    ├── Icons/ICO/                ← multi-resolution .ico (256, 128, 64, 48, 32, 16 px)
    ├── theme.json                ← theme config for the shared engine
    ├── Tools/apply_desktop_icons.py  ← thin shim → Tools/icon_engine.py
    └── Apply_Theme.ps1           ← launcher (Graphite only; others use Tools\Install.bat)
```

The engine lives once at `Tools/icon_engine.py`; each theme only carries a
`theme.json`. The former per-theme applicators were removed.

---

## 🚀 Quick Start

1. `pip install -r requirements.txt` (the engine never auto-installs anything).
2. Open the theme folder (e.g. `Graphite_Elegance_Release`).
3. Launch it:
   - **Graphite Elegance** ships `Apply_Theme.ps1` (Right-click ➔ *Run with PowerShell*).
   - **All themes** have `Tools\Install.bat` (double-click).
   - Or call the engine directly (commands below).

By default this only **applies icons**. Destructive / cosmetic steps are
**opt-in**:

```bat
:: apply icons only (safe default)
python Tools\icon_engine.py --config Graphite_Elegance_Release\theme.json

:: preview without writing anything (no backup, no refresh, no prompt)
python Tools\icon_engine.py --config Graphite_Elegance_Release\theme.json --dry-run

:: hide shortcut names (accessibility: opt-in) and clean launcher duplicates
python Tools\icon_engine.py --config Graphite_Elegance_Release\theme.json --rename --cleanup

:: reorder already-applied shortcuts (theme items only)
python Tools\icon_engine.py --config Graphite_Elegance_Release\theme.json --organize

:: undo a previous run
python Tools\icon_engine.py --restore "%LOCALAPPDATA%\Icons_Engine\backups\<key>\<timestamp>"
```

### Safety
- A **backup is written before any change** (icon edits, deletions and renames
  included) under `%LOCALAPPDATA%\Icons_Engine\backups\<key>\<timestamp>\`.
- `--restore` validates the manifest schema and **only touches paths inside the
  user/public Desktop**; it never deletes arbitrary files.
- `--rename` and `--organize` operate **only on shortcuts that match the active
  theme**.
- `theme.json` is validated strictly: unknown keys are rejected, `persist_key`
  is sanitized and `icons_dir` may not escape the theme folder.

### Note on invisible names
`--rename` uses non-breaking spaces, which makes shortcut names invisible to
screen readers, search and keyboard navigation. It is therefore **opt-in**, not
a default.

---

## 🏭 Regenerating & validating icons

The factory is **reproducible by default**: it only reads the versioned local
assets (`Generator/assets/Raw_Silhouettes`) in a stable order. Network lookups
are opt-in.

```bat
:: factory setup
pip install -r Generator\requirements.txt

:: pin / verify the local source assets
python Generator\scripts\hash_assets.py
python Generator\scripts\hash_assets.py --check

:: local, deterministic generation (verify first with --verify-sources)
python Generator\scripts\generate_premium_icons.py --verify-sources
:: opt-in, non-reproducible:
:: python Generator\scripts\generate_premium_icons.py --online --from-desktop

:: declarative build from pipeline/sources.json (reviewable manifest)
python Generator\pipeline\build.py --check
python Generator\pipeline\build.py --apply --output-dir build_out
python Generator\pipeline\check_output.py build_out

:: PNG/ICO master → multi-resolution .ico (16/32/48/64/128/256)
python Generator\scripts\images_to_ico.py --input <theme>\Icons\ICO --overwrite --recursive

:: gate: fails on incomplete resolutions, bad payloads or duplicate names
python Tools\icon_validate.py --all
```

> **Validation gate:** every released `.ico` carries the full
> 16/32/48/64/128/256 frame set and unique names per variant.
> `python Tools\icon_validate.py --all` → **0 errors, 0 warnings**. The contract
> is documented in [docs/ICON_FORMAT.md](docs/ICON_FORMAT.md).

---

## 🤝 Contributing, License, Security

- [CONTRIBUTING.md](CONTRIBUTING.md) — dev setup, checks, contracts.
- [LICENSE](LICENSE) — MIT (third-party logos excluded).
- [SECURITY.md](SECURITY.md) — safety model and vulnerability reporting.

---
*Developed with mathematical rigor and aesthetic passion. © 2026 Acourd.*
