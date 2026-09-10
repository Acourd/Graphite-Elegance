"""
compare.py — parity check between generated icons and a reference tree
=====================================================================
Compares the 256px frame of generated `.ico` files against a reference theme's
icons (matched by name, case/space-insensitive) and reports the mean absolute
difference (0..255). Useful while migrating a variant to the declarative
pipeline: keep the reference until the difference is acceptable.

Usage: python pipeline/compare.py --generated <dir> --reference <dir>
"""
from __future__ import annotations

import argparse
import os

import numpy as np
from PIL import Image


def norm(name):
    return os.path.splitext(os.path.basename(name))[0].lower().replace(" ", "")


def frame256(path):
    img = Image.open(path)
    best = None
    for i in range(getattr(img, "n_frames", 1)):
        img.seek(i)
        frame = img.copy().convert("RGBA")
        if best is None or frame.size[0] > best.size[0]:
            best = frame
    return best.resize((256, 256), Image.Resampling.LANCZOS)


def index(root):
    found = {}
    for dirpath, _dirs, files in os.walk(root):
        for fname in files:
            if fname.lower().endswith((".ico", ".png")):
                found.setdefault(norm(fname), os.path.join(dirpath, fname))
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description="Parity check (generated vs reference)")
    parser.add_argument("--generated", required=True)
    parser.add_argument("--reference", required=True)
    args = parser.parse_args(argv)

    gen = index(args.generated)
    ref = index(args.reference)
    shared = sorted(set(gen) & set(ref))
    if not shared:
        print("Sin nombres en común.")
        return 1

    results = []
    for key in shared:
        a = np.asarray(frame256(gen[key]), np.float32)
        b = np.asarray(frame256(ref[key]), np.float32)
        mae = float(np.mean(np.abs(a - b)))
        results.append((mae, key))
    results.sort(reverse=True)

    mean = sum(r[0] for r in results) / len(results)
    print(f"comparados={len(results)} MAE_medio={mean:.1f}/255")
    print("peores:")
    for mae, key in results[:10]:
        print(f"  {mae:6.1f}  {key}")
    if mean <= 12:
        print("Paridad visual razonable (MAE <= 12).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
