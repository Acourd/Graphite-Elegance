"""
images_to_ico.py — PNG/JPG/ICO → multi-resolution .ico
======================================================
The conversion stage of the Isoform pipeline, kept separate from the desktop
applicator. Takes already-composed square masters (PNG/JPG) or existing `.ico`
files and emits `.ico` files containing every required size
(16/32/48/64/128/256 by default).

When the input is a `.ico`, its largest frame is used as the source, so this
script doubles as a **repair** tool for icons that only carry a 256px frame.

Usage
-----
    python images_to_ico.py --input Icons/PNG --output ../Graphite_Elegance_Release/Icons/ICO
    python images_to_ico.py --input some.ico --overwrite
    python images_to_ico.py --input Icons --recursive --dry-run

Requires: Pillow (see Generator/requirements.txt).
Exit code 0 = all ok, 1 = some files failed.
"""
from __future__ import annotations

import argparse
import os
import sys

try:
    from PIL import Image
except ImportError:
    print("Falta Pillow. Instala: pip install -r Generator/requirements.txt", file=sys.stderr)
    raise SystemExit(1)

DEFAULT_SIZES = (16, 32, 48, 64, 128, 256)
VALID_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".ico")


def load_base(path):
    """Return a square RGBA master image (largest frame for .ico).

    The source is fully read into memory and closed before any write, so this
    is safe when the output path equals the input (in-place repair).
    """
    with Image.open(path) as img:
        if path.lower().endswith(".ico"):
            best = None
            for i in range(getattr(img, "n_frames", 1)):
                img.seek(i)
                frame = img.copy().convert("RGBA")
                if best is None or frame.size[0] > best.size[0]:
                    best = frame
            img = best if best is not None else img.convert("RGBA")
        else:
            img = img.convert("RGBA")

    side = max(img.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(img, ((side - img.width) // 2, (side - img.height) // 2), img)
    return canvas


def build_ico(base, out_path, sizes):
    """Write an .ico containing exactly `sizes`.

    Pillow's ICO writer generates every requested size from the master image,
    so we hand it a high-quality LANCZOS master and the size list.
    """
    ordered = sorted(int(s) for s in sizes)
    largest = max(ordered)
    master = base.resize((largest, largest), Image.Resampling.LANCZOS)
    master.save(out_path, format="ICO", sizes=[(s, s) for s in ordered])
    return ordered


def collect(input_path, recursive):
    if os.path.isfile(input_path):
        return [input_path]
    files = []
    if recursive:
        for root, _dirs, names in os.walk(input_path):
            files += [os.path.join(root, n) for n in names
                      if n.lower().endswith(VALID_EXT)]
    else:
        files = [os.path.join(input_path, n) for n in os.listdir(input_path)
                 if n.lower().endswith(VALID_EXT)]
    return sorted(files)


def main(argv=None):
    p = argparse.ArgumentParser(description="PNG/JPG/ICO -> multi-resolution .ico")
    p.add_argument("--input", required=True, help="Archivo o carpeta de origen")
    p.add_argument("--output", help="Carpeta destino (por defecto: junto al origen)")
    p.add_argument("--sizes", default=",".join(map(str, DEFAULT_SIZES)),
                   help="Tamaños separados por coma (por defecto 16,32,48,64,128,256)")
    p.add_argument("--recursive", action="store_true")
    p.add_argument("--overwrite", action="store_true", help="Sobrescribir .ico existentes")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    sizes = tuple(sorted({int(x) for x in args.sizes.split(",") if x.strip()}))
    files = collect(args.input, args.recursive)
    if not files:
        print("No se encontraron imágenes.", file=sys.stderr)
        return 1

    ok = fail = skipped = 0
    for src in files:
        name = os.path.splitext(os.path.basename(src))[0] + ".ico"
        if args.output:
            if os.path.isdir(args.input):
                rel = os.path.relpath(os.path.dirname(src), args.input)
                out_dir = os.path.normpath(os.path.join(args.output, rel))
            else:
                out_dir = args.output
        else:
            out_dir = os.path.dirname(src)
        out_path = os.path.join(out_dir, name)

        if os.path.exists(out_path) and not args.overwrite and os.path.abspath(out_path) != os.path.abspath(src):
            print(f"  [SKIP] ya existe {out_path}")
            skipped += 1
            continue
        if args.dry_run:
            print(f"  [DRY] {src} -> {out_path} {list(sizes)}")
            ok += 1
            continue
        try:
            os.makedirs(out_dir, exist_ok=True)
            base = load_base(src)
            done = build_ico(base, out_path, sizes)
            print(f"  [OK] {out_path} -> {done}")
            ok += 1
        except Exception as exc:
            print(f"  [FAIL] {src}: {exc}", file=sys.stderr)
            fail += 1

    print(f"\nGenerados: {ok} | Omitidos: {skipped} | Fallos: {fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
