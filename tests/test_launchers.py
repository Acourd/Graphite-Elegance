import glob
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _bat_launchers():
    patterns = [
        os.path.join(REPO, "*_Release", "Tools", "*.bat"),
        os.path.join(REPO, "*_Release", "*", "Tools", "*.bat"),
    ]
    found = []
    for pattern in patterns:
        found.extend(glob.glob(pattern))
    return sorted(set(found))


def test_there_are_bat_launchers():
    assert _bat_launchers()


def test_bat_launchers_detect_interpreter_once_and_propagate_exit_code():
    for path in _bat_launchers():
        with open(path, encoding="ascii") as fh:
            text = fh.read()
        name = os.path.relpath(path, REPO)
        # Must not re-run the engine as a fallback after a real failure.
        assert "||" not in text, f"{name}: no debe encadenar '||'"
        assert "where py" in text, f"{name}: no detecta el lanzador 'py'"
        assert "where python" in text, f"{name}: no detecta 'python'"
        # Must propagate the engine's exit code.
        assert "exit /b %RC%" in text, f"{name}: no propaga el código de salida"


def test_powershell_launcher_propagates_exit_code():
    path = os.path.join(REPO, "Graphite_Elegance_Release", "Apply_Theme.ps1")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    assert "$LASTEXITCODE" in text
    assert "exit $code" in text
    # The success message must come after the exit-code check.
    assert text.index("$LASTEXITCODE") < text.index("Start-Sleep")
