# Tools — shared icon engine

A single engine applies the icons of **every** theme. Each theme ships only a
`theme.json` plus a minimal launcher (`Tools\Install.bat`, or `Apply_Theme.ps1`)
that calls `Tools/icon_engine.py` with its config — there is no per-theme
applicator code.

## Commands

```bat
:: apply icons only (SAFE DEFAULT: no rename, no cleanup)
python Tools\icon_engine.py --config Graphite_Elegance_Release\theme.json

:: preview — no writes, no Explorer refresh, no prompt
python Tools\icon_engine.py --config Graphite_Elegance_Release\theme.json --dry-run

:: opt-in destructive/cosmetic steps
python Tools\icon_engine.py --config Graphite_Elegance_Release\theme.json --rename --cleanup

:: reorder already-applied shortcuts
python Tools\icon_engine.py --config Graphite_Elegance_Release\theme.json --organize

:: skip the confirmation prompt
python Tools\icon_engine.py --config Graphite_Elegance_Release\theme.json --rename --cleanup --yes

:: undo a run
python Tools\icon_engine.py --restore "%LOCALAPPDATA%\Icons_Engine\backups\<key>\<timestamp>"
```

| Flag | Effect |
|---|---|
| `--config` | Path to the theme config (required, unless `--restore`). |
| `--dry-run` | Plan only. No writes, **no Explorer refresh**, no prompts. |
| `--cleanup` | **Opt-in.** Delete visible launcher duplicates. |
| `--rename` | **Opt-in.** Rename shortcuts to invisible names (accessibility caveat). |
| `--organize` | Reorder already-applied shortcuts per `order`. |
| `--yes` | Do not ask for confirmation. |
| `--allow-duplicate-icons` | Bypass the duplicate-name hard error. |
| `--restore DIR` | Restore icons/names from a backup manifest. |

Exit codes: `0` ok · `1` runtime/dependency error · `2` configuration error.

## Safety model

- **Backup before mutation.** The manifest and copies of every affected file are
  written **before** any change (icon edits, deletions and renames).
- **Validated, all-or-nothing restore.** `--restore` validates the manifest
  schema (including per-file hashes), restricts every path to an allowed
  Desktop root (user + public, or `ISO_DESKTOP_DIRS`) and restores from the
  backed-up files — including the original names. A renamed destination is
  only removed when it still matches the recorded hash; otherwise the entry
  fails safe and nothing else is touched. If any step fails, everything
  already restored is rolled back.
- **Published icons are re-synced.** Every run compares the source icon tree
  with `%LOCALAPPDATA%\Icons_Engine\Themes\<key>\Icons` and republishes when
  assets are missing, changed or obsolete, even if no shortcut needs an update
  (a damaged or stale publication is repaired without touching shortcuts or
  backups).
- **Idempotent re-apply.** The stored icon index is parsed when comparing, so a
  second run over an already-applied theme reports nothing to do.
- **Theme-scoped rename/organize.** `--rename` only renames shortcuts matched to
  the active theme; `--organize` only considers shortcuts whose current icon
  belongs to the theme.
- **No auto-install.** Missing `pywin32` is a hard error pointing to the pinned
  `requirements.txt`.
- **Duplicates by full identity.** `.lnk` identity = target + arguments +
  working directory, so distinct shortcuts are never deleted as duplicates.
- **Duplicate icon names fail.** Two icons resolving to the same key is an
  error (no silent overwrite) unless `--allow-duplicate-icons`.
- **Strict config.** Unknown `theme.json` keys are rejected; `persist_key` is
  sanitized and `icons_dir` may not be absolute or escape the theme folder.
- **Dry-run is inert.** No writes, no backup, no Explorer refresh, no prompt.

## Backup format

```text
%LOCALAPPDATA%\Icons_Engine\backups\<persist_key>\<timestamp>\
├── manifest.json          # schema, theme, created_at, entries[]
└── files\
    └── 0000_Chrome.url    # exact copy of the original file
```

Each `entries[]` item is `{op, path, backup, sha256}` (+ `new_path` and, after a
successful rename, `post_sha256` for `op:"rename"`), where `op` is `modify`,
`delete` or `rename`. Manifests are schema 2 and every entry requires its
SHA-256. Preflight verifies every backup file against its hash before anything
is touched; restoring copies `files/<backup>` back to `path`, re-hashes the
restored bytes and rolls back on mismatch. Schema 1 (legacy, hashless)
manifests are rejected. A renamed `new_path` is removed only
when its `post_sha256` (recorded by an approved, successful rename) exists and
matches; otherwise the entry fails safe and the file is preserved.

## `theme.json`

```json
{
  "name": "Graphite Elegance",
  "persist_key": "Graphite_Elegance_Release",
  "icons_dir": "Icons/ICO",
  "order": ["discord", "chrome", "steam"]
}
```

| Field | Required | Rules |
|---|---|---|
| `name` | yes | non-empty string |
| `persist_key` | yes | `[A-Za-z0-9._-]`, no separators, not `..` |
| `icons_dir` | yes | relative path inside the theme, no `..` |
| `order` | no | list of strings for `--organize` |

Unknown keys are rejected (no silently-ignored config).

## Themes and configs

| Theme | Config |
|---|---|
| Graphite Elegance | `Graphite_Elegance_Release/theme.json` |
| Lumina Frost | `Lumina_Frost_Release/theme.json` |
| White Space Pixel | `White_Space_Pixel_Release/theme.json` |
| KiraLight (Dark) | `KiraLight_Release/DarkVersion/theme.json` |
| KiraLight (Light) | `KiraLight_Release/LightVersion/theme.json` |
| Horizon Glow | `Ooo_Release/theme_horizon_glow.json` |
| Midnight Ooo | `Ooo_Release/theme_midnight_ooo.json` |

## Validation

`Tools/icon_validate.py` is the CI gate (pure Python, cross-platform). It checks
that every variant contains `.ico` files, that each one includes
16/32/48/64/128/256, that names are unique within a variant, and that every
frame actually decodes (PNG chunk CRCs + IDAT decompression; BMP header,
geometry and pixel-data bounds):

```bat
python Tools\icon_validate.py --all
python Tools\icon_validate.py --all --json
```
