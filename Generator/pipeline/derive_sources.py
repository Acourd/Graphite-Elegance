"""
derive_sources.py — bootstrap versioned sources from released icons
==================================================================
When a variant's original sources are lost, this extracts a clean logo
silhouette (PNG with alpha) from each released `.ico` 256px frame and writes it
as a versioned source under ``assets/derived/<slug>/``. The declarative pipeline
can then regenerate the full set deterministically, with close to full parity.

The background is estimated per row from the left/right margins (so gradients
are handled), and the outer margin is ignored so borders/frames are excluded.

Usage:
    python pipeline/derive_sources.py --theme <icons_dir> --out <assets_dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image


def frame256(path):
    img = Image.open(path)
    best = None
    for i in range(getattr(img, "n_frames", 1)):
        img.seek(i)
        frame = img.copy().convert("RGBA")
        if best is None or frame.size[0] > best.size[0]:
            best = frame
    return best


def derive_mask(frame, inset=16, threshold=60.0):
    arr = np.asarray(frame).astype(np.float32)
    rgb, alpha = arr[:, :, :3], arr[:, :, 3]
    h, w = alpha.shape
    mask = np.zeros((h, w), np.uint8)
    xs = list(range(inset, min(inset + 24, w))) + list(range(max(w - inset - 24, 0), w - inset))
    for y in range(inset, h - inset):
        row_rgb, row_a = rgb[y], alpha[y]
        samples = [row_rgb[x] for x in xs if row_a[x] > 200]
        if not samples:
            continue
        bg = np.median(np.array(samples), axis=0)
        dist = np.linalg.norm(row_rgb - bg, axis=1)
        row = (dist > threshold) & (row_a > 200)
        row[:inset] = False
        row[w - inset:] = False
        mask[y] = row.astype(np.uint8) * 255

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    return mask


def save_source(mask, path):
    rgba = np.dstack([np.zeros_like(mask), np.zeros_like(mask), np.zeros_like(mask), mask])
    Image.fromarray(rgba, "RGBA").save(path, format="PNG")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Derive versioned sources from released icons")
    parser.add_argument("--theme", required=True, help="Released icons directory")
    parser.add_argument("--out", required=True, help="Output assets directory")
    parser.add_argument("--inset", type=int, default=16)
    parser.add_argument("--threshold", type=float, default=60.0)
    args = parser.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    lock = {}
    count = 0
    for dirpath, _dirs, files in os.walk(args.theme):
        for fname in sorted(files):
            if not fname.lower().endswith(".ico"):
                continue
            out_name = os.path.splitext(fname)[0] + ".png"
            frame = frame256(os.path.join(dirpath, fname))
            mask = derive_mask(frame, inset=args.inset, threshold=args.threshold)
            if not np.any(mask):
                print(f"  [WARN] máscara vacía: {fname}", file=sys.stderr)
                continue
            out_path = os.path.join(args.out, out_name)
            save_source(mask, out_path)
            lock[out_name] = sha256(out_path)
            count += 1

    lock_path = os.path.join(os.path.dirname(os.path.abspath(args.out)),
                             os.path.basename(os.path.abspath(args.out)) + ".lock.json")
    with open(lock_path, "w", encoding="utf-8") as fh:
        json.dump(lock, fh, indent=2, sort_keys=True)
    print(f"[OK] {count} fuentes derivadas -> {args.out}")
    print(f"[OK] lock -> {lock_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
