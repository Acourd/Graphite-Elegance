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

## Producing icons

Icon generation and repair happen in the **private factory repository**
(silhouette composition + the multi-resolution `.ico` converter). This public
repository only carries the released `.ico` results; if you need to rebuild or
repair a set, do it in the factory and drop the regenerated files in.

## History

Earlier releases used a Pillow save that produced a duplicated `16 px` entry
(`[16, 16, 32, 48, 64, 128, 256]`) in some Graphite and Lumina icons. That was
benign (Windows ignores the duplicate) but non-standard. All such files were
normalized in the factory, so the validator now reports **0 warnings**.
