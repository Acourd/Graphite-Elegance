# Contributing

Thanks for improving Isoform. This project has two halves:

- **`Tools/`** — the desktop engine (applicator/organizer). Windows-only at runtime.
- **`Generator/`** — the icon factory (silhouettes → composed PNG → `.ico`).

## Development setup

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux/mac: source .venv/bin/activate

pip install -r requirements-dev.txt          # engine dev (tests, lint)
pip install -r Generator/requirements.txt    # only if you touch the factory
```

## Running the checks CI runs

```bash
python -m compileall -q Tools Generator/scripts
ruff check Tools tests
pytest
python Tools/icon_validate.py --all          # icon resolution/name gate
```

`icon_validate.py --all` must pass. When you add icons, keep the full frame set
and repair assets with the converter:

```bash
python Generator/scripts/images_to_ico.py \
    --input  <theme>/Icons/ICO --overwrite --recursive
```

## Icon contract

Every released `.ico` must contain **16, 32, 48, 64, 128 and 256 px** frames and
be uniquely named inside its theme variant. The validator enforces this in CI.

### Gradual adoption (baseline)

CI runs strict. For local, incremental work you can opt into a baseline of
known-incomplete files:

```bash
python Tools/icon_validate.py --all --json > audit.json
# take the failing paths, put glob patterns in Tools/icon_baseline.json:
# { "known_incomplete": ["KiraLight_Release/**"] }
python Tools/icon_validate.py --all --baseline Tools/icon_baseline.json
```

## Theme contract (`theme.json`)

| Field | Required | Rules |
|---|---|---|
| `name` | yes | non-empty string |
| `persist_key` | yes | `[A-Za-z0-9._-]`, no separators, not `..` |
| `icons_dir` | yes | relative path inside the theme folder, no `..` |
| `order` | no | list of strings used by `--organize` |

The engine validates this before touching any path.

## Pull requests

1. Keep the engine cross-platform **importable** (COM access stays lazy).
2. Add or update tests for behavior changes (`tests/`).
3. Run the checks above.
4. Do not commit generated caches, `__pycache__`, or unlicensed brand assets.
5. Describe *why* in the PR body; keep commits focused.

By contributing you agree your work is licensed under the repo `LICENSE`.
