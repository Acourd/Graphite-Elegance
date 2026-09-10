"""
build.py — declarative, reproducible build of the icon factory outputs
=====================================================================
Drives the pipeline from a reviewable manifest (``sources.json``): every output
icon is mapped to a versioned local source, a style and an output folder. It
never inspects the operator's Desktop and never downloads anything.

Usage
-----
    python pipeline/build.py --check                 # verify manifest + hashes
    python pipeline/build.py --apply                 # compose and write in place
    python pipeline/build.py --apply --only Graphite_Elegance_Release
    python pipeline/build.py --apply --output-dir <dir>

``--check`` only needs the stdlib; ``--apply`` additionally needs Pillow,
OpenCV and NumPy (see Generator/requirements.txt).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

PIPELINE = os.path.dirname(os.path.abspath(__file__))
GENERATOR = os.path.dirname(PIPELINE)
REPO = os.path.dirname(GENERATOR)
SOURCES = os.path.join(PIPELINE, "sources.json")
RAW = os.path.join(GENERATOR, "assets", "Raw_Silhouettes")
LOCK = os.path.join(GENERATOR, "assets", "Raw_Silhouettes.lock.json")

if PIPELINE not in sys.path:
    sys.path.insert(0, PIPELINE)
from styles import STYLES  # noqa: E402

KNOWN_STYLES = set(STYLES)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path=SOURCES):
    with open(path, "r", encoding="utf-8-sig") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or not isinstance(data.get("themes"), list):
        raise ValueError("sources.json inválido: falta 'themes'")
    return data


def _within(child, parent):
    child, parent = os.path.abspath(child), os.path.abspath(parent)
    try:
        return child == parent or os.path.commonpath([child, parent]) == parent
    except ValueError:
        return False


def verify(manifest, repo=REPO):
    """Return a list of problems with the manifest/sources (empty = ok)."""
    errors = []
    lock = {}
    if os.path.isfile(LOCK):
        with open(LOCK, "r", encoding="utf-8") as fh:
            lock = json.load(fh)

    for theme in manifest["themes"]:
        name = theme.get("name", "?")
        style = theme.get("style")
        if style not in KNOWN_STYLES:
            errors.append(f"{name}: estilo desconocido {style!r}")
        icons_dir = os.path.join(repo, theme.get("icons_dir", ""))
        if not _within(icons_dir, repo):
            errors.append(f"{name}: icons_dir sale del repo")
        outputs = set()
        for target in theme.get("targets", []):
            source = target.get("source")
            output = target.get("output")
            if not source or not output:
                errors.append(f"{name}: target sin source/output")
                continue
            src_path = os.path.join(RAW, source)
            if not os.path.isfile(src_path):
                errors.append(f"{name}: falta la fuente {source}")
            elif source in lock and sha256(src_path) != lock[source]:
                errors.append(f"{name}: hash distinto para {source}")
            key = output.lower()
            if key in outputs:
                errors.append(f"{name}: salida duplicada {output}")
            outputs.add(key)
    return errors


def apply(manifest, repo=REPO, only=None, output_dir=None):
    if PIPELINE not in sys.path:
        sys.path.insert(0, PIPELINE)  # allow direct execution (also embeddable Python)
    from compose import ICON_SIZES, compose_from_file, save_ico, save_png  # noqa: E402

    base = os.path.abspath(output_dir or repo)
    built = 0
    for theme in sorted(manifest["themes"], key=lambda t: t["name"]):
        if only and theme["name"] != only:
            continue
        style = theme["style"]
        ico_dir = os.path.join(base, theme["icons_dir"])
        png_dir = os.path.join(base, theme["png_dir"]) if theme.get("png_dir") else None
        for target in sorted(theme["targets"], key=lambda t: t["output"].lower()):
            src = os.path.join(RAW, target["source"])
            renders = compose_from_file(src, style, sizes=ICON_SIZES)
            os.makedirs(ico_dir, exist_ok=True)
            save_ico(renders, os.path.join(ico_dir, f"{target['output']}.ico"))
            if png_dir:
                os.makedirs(png_dir, exist_ok=True)
                save_png(renders, os.path.join(png_dir, f"{target['output']}.png"))
            built += 1
            print(f"  [OK] {theme['name']}/{target['output']}")
    print(f"\nGenerados: {built} iconos.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build declarativo de iconos Isoform")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true", help="Verificar manifiesto y hashes")
    action.add_argument("--apply", action="store_true", help="Componer y escribir los iconos")
    parser.add_argument("--only", help="Limitar a un tema (nombre de la carpeta Release)")
    parser.add_argument("--output-dir", help="Raíz de salida alternativa (para pruebas)")
    args = parser.parse_args(argv)

    manifest = load_manifest()
    problems = verify(manifest)
    if problems:
        for problem in problems:
            print(f"  [FAIL] {problem}", file=sys.stderr)
        print(f"\n{len(problems)} problemas en el manifiesto.", file=sys.stderr)
        return 1

    if args.check:
        total = sum(len(t["targets"]) for t in manifest["themes"])
        print(f"[OK] manifiesto válido: {len(manifest['themes'])} temas, {total} objetivos.")
        return 0

    return apply(manifest, only=args.only, output_dir=args.output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
