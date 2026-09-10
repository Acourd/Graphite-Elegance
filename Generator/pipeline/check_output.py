"""
check_output.py — validate a tree of generated .ico files
=========================================================
Used by CI after ``build.py --apply`` to a temporary directory. Checks that
every ``.ico`` under the given root has the required frame set and a decodable
payload (reusing Tools/icon_validate.inspect_ico).

Usage: python pipeline/check_output.py <dir>
"""
from __future__ import annotations

import argparse
import os
import sys

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "Tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
from icon_validate import REQUIRED_ICO_SIZES, inspect_ico  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate generated .ico files")
    parser.add_argument("root")
    args = parser.parse_args(argv)

    checked = bad = 0
    for dirpath, _dirs, files in os.walk(args.root):
        for fname in sorted(files):
            if not fname.lower().endswith(".ico"):
                continue
            checked += 1
            path = os.path.join(dirpath, fname)
            sizes, errors, _warnings = inspect_ico(path)
            missing = [s for s in REQUIRED_ICO_SIZES if s not in sizes]
            if errors or missing:
                bad += 1
                print(f"FAIL {path}: {errors or missing}")
    print(f"{checked} .ico revisados, {bad} con problemas")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
