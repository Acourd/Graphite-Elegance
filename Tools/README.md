# Tools — shared icon engine

A single engine applies the icons of **every** theme. Each theme ships only a
`theme.json`; its `Tools/apply_desktop_icons.py` is a thin shim to
`Tools/icon_engine.py`.

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
- **Validated restore.** `--restore` validates the manifest schema, restricts
  every path to an allowed Desktop root (user + public, or `ISO_DESKTOP_DIRS`)
  and rewrites from the backed-up files — including the original names.
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

Each `entries[]` item is `{op, path, backup}` (+ `new_path` for `op:"rename"`),
where `op` is `modify`, `delete` or `rename`. Restoring copies `files/<backup>`
back to `path` and, for renames, removes `new_path` first.

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
that every released `.ico` contains 16/32/48/64/128/256 and that names are unique
within a variant:

```bat
python Tools\icon_validate.py --all
python Tools\icon_validate.py --all --json
```
