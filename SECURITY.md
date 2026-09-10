# Security Policy

## Supported Versions

This is a personal project maintained on `main`. Only the latest revision is
supported.

## Reporting a Vulnerability

Please **do not** open a public issue for security problems. Instead, report
privately via GitHub Security Advisories ("Report a vulnerability") or by
contacting the maintainer through the profile linked in `README.md`.

You can expect an acknowledgement within a reasonable time. Include:

- affected file(s) / command,
- a minimal reproduction,
- the impact you understand.

## Design notes relevant to safety

The desktop engine (`Tools/icon_engine.py`) modifies user data, so it is built
with explicit safety guards:

- **No auto-install.** The engine never runs `pip`. Missing `pywin32` is a hard
  error that points to the pinned `requirements.txt`.
- **Opt-in mutations.** Deleting duplicates (`--cleanup`) and renaming shortcuts
  to invisible names (`--rename`) are off by default.
- **Dry-run.** `--dry-run` performs no writes and no Explorer refresh.
- **Backups.** Every mutation is recorded under
  `%LOCALAPPDATA%\Icons_Engine\backups\<persist_key>\<timestamp>\manifest.json`
  and can be reverted with `--restore <dir>`.
- **Validated config.** `persist_key` and `icons_dir` are validated before being
  used in filesystem paths (no absolute paths, no `..` traversal).

## Third-party trademarks

Icon renders may embed third-party logos (SimpleIcons / Clearbit). They are the
property of their owners; verify your rights before redistribution.
