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
SKIP_DIRS = {".git", "Tools", "tests", "node_modules", ".github"}


# ---------------------------------------------------------------------------
def inspect_ico(path):
    """Return (sizes, errors, warnings) with structural + payload checks."""
    sizes, errors, warnings = [], [], []
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError as exc:
        return sizes, [f"no se pudo leer: {exc}"], warnings

    if len(data) < 6:
        return sizes, ["archivo demasiado corto"], warnings
    reserved, itype, count = struct.unpack_from("<HHH", data, 0)
    if reserved != 0 or itype != 1:
        return sizes, ["no es un .ico (cabecera inválida)"], warnings
    if count == 0:
        return sizes, ["sin entradas de imagen"], warnings
    if len(data) < 6 + count * 16:
        return sizes, ["tabla de entradas truncada"], warnings

    for i in range(count):
        off = 6 + i * 16
        w, h, _col, _res, _planes, _bpp, size, dataoff = struct.unpack_from("<BBBBHHII", data, off)
        w = 256 if w == 0 else w
        h = 256 if h == 0 else h
        sizes.append(w)
        if w != h:
            errors.append(f"entrada {i}: no cuadrada ({w}x{h})")
        if not (1 <= w <= 256):
            errors.append(f"entrada {i}: tamaño fuera de rango ({w})")
        if size <= 0 or dataoff + size > len(data):
            errors.append(f"entrada {i}: payload fuera de límites")
            continue
        head = data[dataoff:dataoff + 8]
        is_png = head.startswith(b"\x89PNG\r\n\x1a\n")
        is_bmp = head[:4] in (b"\x28\x00\x00\x00", b"\x0c\x00\x00\x00")
        if not (is_png or is_bmp):
            errors.append(f"entrada {i}: payload no decodificable (ni PNG ni BMP)")
    if len(set(sizes)) != len(sizes):
        warnings.append(f"entradas de tamaño duplicadas {sorted(sizes)}")
    return sizes, errors, warnings


def read_ico_sizes(path):
    """Backwards-compatible: (sizes, first_error)."""
    sizes, errors, _warnings = inspect_ico(path)
    return sizes, (errors[0] if errors else None)


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
            sizes, errs, warns = inspect_ico(fpath)
            covered_by_baseline = baseline and any(fnmatch.fnmatch(rel, p) for p in baseline)
            for err in errs:
                if covered_by_baseline:
                    result["warnings"].append(f"(baseline) {rel}: {err}")
                else:
                    result["errors"].append(f"{rel}: {err}")
            for warn in warns:
                result["warnings"].append(f"{rel}: {warn}")
            missing = [s for s in required if s not in sizes]
            if missing:
                text = f"{rel}: faltan {missing}"
                if covered_by_baseline:
                    result["warnings"].append(f"(baseline) {text}")
                else:
                    result["errors"].append(text)
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
