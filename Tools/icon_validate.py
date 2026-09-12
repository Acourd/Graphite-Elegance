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
import zlib

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


def _rel(path, start):
    """relpath that survives being on a different Windows drive (C: vs D:)."""
    try:
        return os.path.relpath(path, start)
    except ValueError:
        return os.path.abspath(path)


# ---------------------------------------------------------------------------
def _png_errors(payload, w, h):
    """Deep PNG check: chunk CRCs, IHDR, IEND and a real IDAT decompression."""
    errors = []
    if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return ["no es PNG"]
    pos = 8
    idat = b""
    header = None
    seen_iend = False
    while pos + 8 <= len(payload):
        length, ctype = struct.unpack_from(">I4s", payload, pos)
        pos += 8
        if pos + length + 4 > len(payload):
            errors.append("chunk PNG truncado")
            return errors
        body = payload[pos:pos + length]
        crc = struct.unpack_from(">I", payload, pos + length)[0]
        if zlib.crc32(ctype + body) & 0xffffffff != crc:
            errors.append(f"CRC inválido en {ctype.decode('latin1', 'replace')}")
        if ctype == b"IHDR":
            if length != 13:
                errors.append("IHDR inválido")
                return errors
            header = struct.unpack(">IIBBBBB", body)
        elif ctype == b"IDAT":
            idat += body
        elif ctype == b"IEND":
            seen_iend = True
        pos += length + 4
    if header is None:
        return errors + ["sin IHDR"]
    if not seen_iend:
        errors.append("sin IEND")
    if not idat:
        errors.append("sin IDAT")
    pw, ph, depth, color, comp, filt, interlace = header
    if (pw, ph) != (w, h):
        errors.append(f"dimensiones PNG {pw}x{ph} != {w}x{h}")
    if comp != 0 or filt != 0:
        errors.append("compresión/filtro PNG no soportados")
    if interlace != 0:
        errors.append("PNG entrelazado no soportado")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color)
    if channels is None:
        errors.append(f"color type PNG inválido ({color})")
    elif idat:
        rowbytes = (pw * depth * channels + 7) // 8
        expected = ph * (1 + rowbytes)
        try:
            raw = zlib.decompress(idat)
        except zlib.error as exc:
            errors.append(f"IDAT no descomprime: {exc}")
        else:
            if len(raw) != expected:
                errors.append(f"IDAT descomprimido {len(raw)} bytes != {expected}")
    return errors


def _bmp_errors(payload, w, h):
    """BMP-in-ICO check: header, geometry, depth and pixel-data bounds."""
    errors = []
    if len(payload) < 40:
        return ["BMP truncado"]
    size, bw, bh, planes, bpp, compression = struct.unpack_from("<IiiHHI", payload, 0)
    if size < 40 or size > len(payload):
        errors.append("BITMAPINFOHEADER inválido")
        return errors
    if bw != w:
        errors.append(f"ancho BMP {bw} != {w}")
    if abs(bh) not in (h, 2 * h):
        errors.append(f"alto BMP {abs(bh)} != {h}")
    if planes != 1:
        errors.append("planes BMP != 1")
    if bpp not in (1, 4, 8, 16, 24, 32):
        errors.append(f"bpp BMP inválido ({bpp})")
    if compression not in (0, 3):
        errors.append(f"compresión BMP no soportada ({compression})")
    if not errors:
        stride = ((w * bpp + 31) // 32) * 4
        palette = 4 * (1 << bpp) if bpp <= 8 else 0
        masks = 12 if compression == 3 else 0
        if len(payload) < size + masks + palette + stride * h:
            errors.append("datos de píxel BMP truncados")
    return errors


def inspect_ico(path):
    """Return (sizes, errors, warnings) with structural + deep payload checks."""
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
        payload = data[dataoff:dataoff + size]
        if payload.startswith(b"\x89PNG\r\n\x1a\n"):
            errs = _png_errors(payload, w, h)
        elif payload[:4] in (b"\x28\x00\x00\x00", b"\x0c\x00\x00\x00"):
            errs = _bmp_errors(payload, w, h)
        else:
            errs = ["payload no decodificable (ni PNG ni BMP)"]
        errors.extend(f"entrada {i}: {err}" for err in errs)
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
    result = {"config": _rel(config_path, REPO),
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
            rel = _rel(fpath, REPO)
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

    if result["checked"] == 0:
        result["errors"].append(f"no contiene archivos .ico: {icons_dir}")

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
