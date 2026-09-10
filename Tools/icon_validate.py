"""
Isoform - icon validator  ·  cross-platform
===========================================
Validates released icon sets *without* touching the desktop and without any
platform dependency. Designed to run in CI.

Checks per theme variant:
  1. theme.json is valid (reuses icon_engine.load_config).
  2. icons_dir exists and contains .ico files.
  3. every .ico is a well-formed ICO and includes all required sizes
     (16/32/48/64/128/256 by default).
  4. no duplicate icon names (case/space-insensitive) inside the variant.

Usage
-----
    python Tools/icon_validate.py --all
    python Tools/icon_validate.py --config Graphite_Elegance_Release/theme.json
    python Tools/icon_validate.py --all --json
    python Tools/icon_validate.py --all --baseline Tools/icon_baseline.json

Exit code 0 = compliant, 1 = failures.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import struct
import sys

# Allow running the script directly (also under embeddable Python, which does
# not add the script directory to sys.path).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from icon_engine import (  # noqa: E402, I001
    REQUIRED_ICO_SIZES,
    ConfigError,
    IconNameError,
    index_icons,
    load_config,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", "Generator", "Tools", "tests", "node_modules", ".github"}


# ---------------------------------------------------------------------------
def read_ico_sizes(path):
    """Return (sizes, error). sizes is a list of ints (256 for 0)."""
    try:
        with open(path, "rb") as fh:
            header = fh.read(6)
            if len(header) < 6:
                return [], "archivo demasiado corto"
            reserved, itype, count = struct.unpack("<HHH", header)
            if reserved != 0 or itype != 1:
                return [], "no es un .ico (cabecera inválida)"
            if count == 0:
                return [], "sin entradas de imagen"
            entries = fh.read(count * 16)
            if len(entries) < count * 16:
                return [], "tabla de entradas truncada"
    except OSError as exc:
        return [], f"no se pudo leer: {exc}"

    sizes = []
    for i in range(count):
        w = entries[i * 16]
        sizes.append(256 if w == 0 else w)
    return sizes, None


# ---------------------------------------------------------------------------
def discover_configs(root):
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for f in filenames:
            if fnmatch.fnmatch(f, "theme*.json"):
                found.append(os.path.join(dirpath, f))
    return sorted(found)


def validate_config(config_path, required=REQUIRED_ICO_SIZES, baseline=None):
    result = {"config": os.path.relpath(config_path, REPO),
              "name": None, "errors": [], "warnings": [], "checked": 0}

    try:
        cfg = load_config(config_path)
    except ConfigError as exc:
        result["errors"].append(str(exc))
        return result

    result["name"] = cfg["name"]
    icons_dir = cfg["icons_path"]
    if not os.path.isdir(icons_dir):
        result["errors"].append(f"icons_dir no existe: {icons_dir}")
        return result

    try:
        index_icons(icons_dir)  # raises on duplicate names
    except IconNameError as exc:
        result["errors"].append(str(exc))

    missing_by_size = {}
    for dirpath, _dirs, files in os.walk(icons_dir):
        for fname in sorted(files):
            if not fname.lower().endswith(".ico"):
                continue
            result["checked"] += 1
            fpath = os.path.join(dirpath, fname)
            rel = os.path.relpath(fpath, REPO)
            sizes, err = read_ico_sizes(fpath)
            if err:
                result["errors"].append(f"{rel}: {err}")
                continue
            missing = [s for s in required if s not in sizes]
            if len(set(sizes)) != len(sizes):
                result["warnings"].append(f"{rel}: entradas de tamaño duplicadas {sorted(sizes)}")
            if missing:
                covered = f"{rel}: faltan {missing}"
                if baseline and any(fnmatch.fnmatch(rel, p) for p in baseline):
                    result["warnings"].append(f"(baseline) {covered}")
                else:
                    result["errors"].append(covered)
                    for s in missing:
                        missing_by_size[s] = missing_by_size.get(s, 0) + 1

    if missing_by_size:
        result["warnings"].append("tamaños faltantes: " +
                                  ", ".join(f"{s}px x{n}" for s, n in sorted(missing_by_size.items())))
    return result


# ---------------------------------------------------------------------------
def main(argv=None):
    p = argparse.ArgumentParser(description="Validador de iconos Isoform")
    p.add_argument("--config", help="Validar un solo theme.json")
    p.add_argument("--all", action="store_true", help="Validar todos los theme*.json del repo")
    p.add_argument("--json", action="store_true", help="Salida JSON")
    p.add_argument("--baseline", help="JSON con patrones conocidos-fallidos (modo adopción gradual)")
    args = p.parse_args(argv)

    if not args.all and not args.config:
        p.error("Usa --all o --config")

    baseline = None
    if args.baseline and os.path.isfile(args.baseline):
        with open(args.baseline, "r", encoding="utf-8") as fh:
            baseline = json.load(fh).get("known_incomplete", [])

    configs = discover_configs(REPO) if args.all else [os.path.abspath(args.config)]
    results = [validate_config(c, baseline=baseline) for c in configs]

    total_errors = sum(len(r["errors"]) for r in results)
    total_warn = sum(len(r["warnings"]) for r in results)

    if args.json:
        print(json.dumps({"results": results,
                          "errors": total_errors, "warnings": total_warn}, indent=2))
    else:
        for r in results:
            status = "OK " if not r["errors"] else "FAIL"
            print(f"[{status}] {r['config']}  ({r['name']})  {r['checked']} .ico")
            for e in r["errors"]:
                print(f"        ERROR  {e}")
            for wr in r["warnings"]:
                print(f"        warn   {wr}")
        print(f"\n{len(results)} variantes · {total_errors} errores · {total_warn} avisos")

    return 1 if total_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
