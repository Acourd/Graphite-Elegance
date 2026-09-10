# Generator — icon factory

Scripts that **generate** the `.ico` files of every theme from source
silhouettes. This is the factory that was missing from the repository; it was
restored from the backup `Backup_Aycozen_20260611_022103`.

> The themes published in `../<Theme>_Release/Icons/` are the **output** of
> these scripts. The desktop applicator lives in `../Tools/`.

## Structure

```text
Generator/
├── scripts/                 ← Python pipeline
│   └── _legacy_appliers/    ← old applicators (historical, do not use)
├── pipeline/                ← declarative build (sources.json + build.py)
├── assets/
│   └── Raw_Silhouettes/     ← source logos (PNG / JPG / ICO) + .lock.json
├── requirements.txt
└── README.md
```

## Declarative build (`pipeline/`)

`pipeline/sources.json` maps every reproducible output to a versioned local
source, a style and an output folder. `pipeline/build.py` drives it:

```bat
python pipeline\build.py --check                                   :: manifest + hashes (stdlib only)
python pipeline\build.py --apply                                   :: compose in place
python pipeline\build.py --apply --only Graphite_Elegance_Release   :: one theme
python pipeline\build.py --apply --output-dir build_out            :: to a scratch dir
python pipeline\check_output.py build_out                          :: validate generated .ico
```

Styles: `graphite` (dark) and `lumina` (light). No Desktop access, no network,
stable order — the same sources always yield the same frames.

## Pipeline

1. **Source** — `assets/Raw_Silhouettes/` or download online
   (SimpleIcons SVG → Clearbit → Google favicon).
2. **Silhouette** — `extract_silhouette()` (OpenCV): real alpha, or CIELab
   distance to the background colour + small-hole filling.
3. **Composition** — squircle with gradient, inner border and dual shadow,
   rendered at `size × 4` (supersampling) and downscaled with LANCZOS.
4. **Export** — multi-resolution `.ico` (256/128/64/48/32/16) + 256 px master PNG.

## Reproducibility

Generation is **deterministic by default**:

- Only the versioned local assets in `assets/Raw_Silhouettes/` are read, in
  sorted order; the operator's Desktop is **not** inspected.
- Network lookups (SimpleIcons / Clearbit / favicon) are **opt-in** and are
  inherently mutable, so they are never part of the default path.
- `assets/Raw_Silhouettes.lock.json` pins the SHA-256 of every local source.
  Verify with `hash_assets.py --check` (also run in CI).

```bat
python scripts\hash_assets.py            :: (re)build the lock
python scripts\hash_assets.py --check    :: fail on source drift
python scripts\generate_premium_icons.py --verify-sources
:: opt-in, non-reproducible:
:: python scripts\generate_premium_icons.py --online --from-desktop
```

## Scripts

| Script | Status | What it does |
|---|---|---|
| `generate_premium_icons.py` | ✅ main | Full Graphite pipeline. Reproducible from local sources; `_Review` quarantine, pretty names. `--online`/`--from-desktop` opt into non-reproducible sources. |
| `graphite_compose.py` | ✅ | Composes a fixed list from `Raw_Silhouettes` with the Graphite style. |
| `lumina_compose.py` | ✅ | Same as above but Lumina Frost style (light, dark logo). |
| `generate_graphite.py` | ✅ | First version of the Graphite generator. |
| `images_to_ico.py` | ✅ conversion | PNG/JPG/ICO master → multi-resolution `.ico` (16/32/48/64/128/256). Does **not** composite; also **repairs** 256-only icons. |
| `hash_assets.py` | ✅ | Builds/verifies `assets/Raw_Silhouettes.lock.json` (SHA-256). |
| `graphite_builder.py` | ⚠️ optional | Alternative render via SVG + Playwright/Chromium. |
| `generate_icons.py`, `process_raw.py`, `make_preview.py` | ⚠️ legacy | Early prototypes; they write under `Generator/`. |
| `premium_upgrade.py` | ⚠️ legacy | One-off migration from a "Premium" set (`_premium_in/`). |
| `design_logos.py`, `draw_custom_logos.py`, `refine_logos.py`, `fix_custom_icons.py`, `finalize_premium.py`, `normalize_names.py`, `process_exe.py`, `qa_evaluate.py`, `qa_icons.py`, `check_lumina_contrast.py`, `convert_webp.py`, `debug_svg.py` | ⚠️ legacy | Helper utilities. Some still contain old absolute paths (`E:\...`): check them before use. |

The ✅ scripts already use **repo-relative paths** (`Generator/scripts/` → repo
root) and are the recommended entry points.

## Usage

```bat
pip install -r requirements.txt

:: Verify pinned sources, then generate locally (deterministic)
python scripts\hash_assets.py --check
python scripts\generate_premium_icons.py --verify-sources

:: Lumina Frost style (Videojuegos category)
python scripts\lumina_compose.py

:: Alternative via Chromium (requires: pip install playwright && playwright install chromium)
python scripts\graphite_builder.py

:: Conversion stage: composed PNG/ICO master -> multi-resolution .ico
python scripts\images_to_ico.py --input ..\Graphite_Elegance_Release\Icons\PNG ^
    --output ..\Graphite_Elegance_Release\Icons\ICO --overwrite

:: Repair existing icons that only carry a 256px frame
python scripts\images_to_ico.py --input ..\KiraLight_Release\DarkVersion\Icons\ICO --overwrite
```

Output:
- `Graphite_Elegance_Release/Icons/ICO/` and `.../Icons/PNG/`
- `Lumina_Frost_Release/Icons/ICO/`

## Notes

- `rembg` is optional: if installed, it improves the cut-out of photorealistic
  sources with a background.
- Third-party logos come from SimpleIcons / Clearbit; their use is subject to
  the corresponding trademarks.
