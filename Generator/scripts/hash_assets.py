"""
hash_assets.py — pin the local source assets (reproducibility)
==============================================================
Builds/verifies ``Generator/assets/Raw_Silhouettes.lock.json``: a sorted map of
filename -> SHA-256 for every file in ``Raw_Silhouettes``. ``generate_*`` can
then refuse to run when a source was modified.

Usage:
    python hash_assets.py            # (re)build the lock
    python hash_assets.py --check    # verify and exit non-zero on drift
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
GENERATOR = os.path.dirname(SCRIPTS)
RAW = os.path.join(GENERATOR, "assets", "Raw_Silhouettes")
LOCK = os.path.join(GENERATOR, "assets", "Raw_Silhouettes.lock.json")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_map():
    return {name: sha256(os.path.join(RAW, name)) for name in sorted(os.listdir(RAW))
            if os.path.isfile(os.path.join(RAW, name))}


def build():
    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    data = current_map()
    with open(LOCK, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
    print(f"[OK] {len(data)} hashes -> {LOCK}")
    return 0


def check():
    if not os.path.isfile(LOCK):
        print(f"[FAIL] no existe {LOCK}; ejecuta hash_assets.py", file=sys.stderr)
        return 1
    with open(LOCK, "r", encoding="utf-8") as fh:
        locked = json.load(fh)
    actual = current_map()
    problems = []
    for name, digest in locked.items():
        if name not in actual:
            problems.append(f"falta {name}")
        elif actual[name] != digest:
            problems.append(f"hash distinto {name}")
    for name in sorted(set(actual) - set(locked)):
        problems.append(f"nuevo sin fijar {name}")
    if problems:
        for problem in problems:
            print(f"  [DRIFT] {problem}", file=sys.stderr)
        return 1
    print(f"[OK] {len(locked)} fuentes verificadas")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lock/verify Raw_Silhouettes hashes")
    parser.add_argument("--check", action="store_true", help="Verify instead of rebuild")
    args = parser.parse_args()
    raise SystemExit(check() if args.check else build())
