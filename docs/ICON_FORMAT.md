# Icon format & validation

Isoform ships Windows `.ico` files with a fixed set of frames. This document is
the contract enforced by `Tools/icon_validate.py` and CI.

## Required frames

Every released `.ico` must contain **all** of:

| Size | Purpose |
|---:|---|
| 16 px | taskbar / small lists |
| 32 px | desktop small icons |
| 48 px | medium icons |
| 64 px | large icons |
| 128 px | extra-large icons |
| 256 px | thumbnails / high-DPI |

Additionally, **names must be unique within a theme variant** (case- and
space-insensitive). Two icons resolving to the same key is an error — the
applicator would otherwise overwrite one silently.

## Running the gate

```bash
python Tools/icon_validate.py --all            # human output, non-zero on errors
python Tools/icon_validate.py --all --json     # machine output
python Tools/icon_validate.py --config Graphite_Elegance_Release/theme.json
```

CI runs `--all` on every push/PR (`.github/workflows/ci.yml`, job
`validate-icons`). The intended state is:

```
7 variantes · 0 errores · 0 avisos
```

`--allow-duplicate-icons` exists only as a **local escape hatch** for the
applicator; it must **not** be used in CI.

## Building / repairing icons

`Generator/scripts/images_to_ico.py` is the conversion stage. It accepts a
composed PNG/JPG master or an existing `.ico` (using its largest frame) and
rewrites a clean multi-resolution file:

```bash
# one theme, in place
python Generator/scripts/images_to_ico.py \
    --input Lumina_Frost_Release/Icons/ICO --overwrite --recursive

# a single file, different output folder
python Generator/scripts/images_to_ico.py --input master.png --output out/
```

## History

Earlier releases used a Pillow save that produced a duplicated `16 px` entry
(`[16, 16, 32, 48, 64, 128, 256]`) in some Graphite and Lumina icons. That was
benign (Windows ignores the duplicate) but non-standard. All such files were
normalized with `images_to_ico.py`, so the validator now reports **0 warnings**.
Keep new assets going through the converter to preserve this.
