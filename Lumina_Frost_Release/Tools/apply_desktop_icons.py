"""
Aplicador unificado de Isoform.
Delega en ``Tools/icon_engine.py`` (raíz del repo) usando theme.json.
Ejecuta con:  python apply_desktop_icons.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_THEME_DIR = os.path.dirname(_HERE)
_CONFIG = os.path.join(_THEME_DIR, "theme.json")

# Localiza el motor unificado subiendo por el árbol del repo
_root = _HERE
while os.path.dirname(_root) != _root and not os.path.isfile(os.path.join(_root, "Tools", "icon_engine.py")):
    _root = os.path.dirname(_root)
_engine_dir = os.path.join(_root, "Tools")
if _engine_dir not in sys.path:
    sys.path.insert(0, _engine_dir)

from icon_engine import run_cli  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(run_cli(config_path=_CONFIG))
