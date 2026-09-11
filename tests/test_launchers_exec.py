"""Real launcher execution tests (Windows only).

They prepend a fake ``py``/``python`` interpreter to PATH and run the actual
theme launchers, asserting they resolve the interpreter once and propagate its
exit code (no ``||`` re-run).
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows launchers only")


def _write_fake(fake_dir):
    body = '@echo off\r\necho %~n0 %*>>"%ISO_FAKE_LOG%"\r\nexit /b %ISO_FAKE_RC%\r\n'
    for name in ("py.bat", "python.bat"):
        with open(fake_dir / name, "w", encoding="ascii", newline="") as fh:
            fh.write(body)


def _run(script, tmp_path, rc):
    fake_dir = tmp_path / "fakebin"
    fake_dir.mkdir(exist_ok=True)
    _write_fake(fake_dir)
    log = tmp_path / "calls.log"
    env = os.environ.copy()
    env["PATH"] = str(fake_dir) + os.pathsep + env.get("PATH", "")
    env["ISO_FAKE_LOG"] = str(log)
    env["ISO_FAKE_RC"] = str(rc)
    if script.suffix.lower() == ".bat":
        command = ["cmd", "/c", str(script)]
    else:
        command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)]
    proc = subprocess.run(command, input=b"\n", capture_output=True, env=env, timeout=60)
    calls = log.read_text(encoding="ascii").splitlines() if log.exists() else []
    return proc.returncode, calls


def test_bat_launcher_propagates_error_without_rerun(tmp_path):
    bat = REPO / "Graphite_Elegance_Release" / "Tools" / "Install.bat"
    code, calls = _run(bat, tmp_path, rc=9)
    assert code == 9
    assert len(calls) == 1, calls  # a '|| python' fallback would run twice


def test_bat_launcher_success_returns_zero(tmp_path):
    bat = REPO / "Ooo_Release" / "Tools" / "apply_horizon_glow.bat"
    code, calls = _run(bat, tmp_path, rc=0)
    assert code == 0
    assert len(calls) == 1


def test_powershell_launcher_propagates_error(tmp_path):
    ps1 = REPO / "Graphite_Elegance_Release" / "Apply_Theme.ps1"
    code, calls = _run(ps1, tmp_path, rc=9)
    assert code == 9
    assert len(calls) == 1
