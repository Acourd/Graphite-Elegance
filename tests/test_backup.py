import json
import os

import pytest

from icon_engine import (
    BackupError,
    _safe_backup_file,
    create_backup,
    is_within,
    validate_manifest,
)


def test_is_within():
    roots = [os.path.abspath("/home/u/Desktop")]
    assert is_within("/home/u/Desktop/a.lnk", roots)
    assert not is_within("/home/u/Desktop2/a.lnk", roots)
    assert not is_within("/home/u/Desktop/../secret", roots)
    assert not is_within("/home/u/Desktop", roots)  # the root itself is not a file


def test_safe_backup_file_rejects_traversal(tmp_path):
    with pytest.raises(BackupError):
        _safe_backup_file(str(tmp_path), "../evil.ico")
    with pytest.raises(BackupError):
        _safe_backup_file(str(tmp_path), "/abs/evil.ico")
    with pytest.raises(BackupError):
        _safe_backup_file(str(tmp_path), "")


def _desktop(tmp_path, monkeypatch):
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    monkeypatch.setenv("ISO_DESKTOP_DIRS", str(desktop))
    return desktop


def test_validate_manifest_ok(tmp_path, monkeypatch):
    desktop = _desktop(tmp_path, monkeypatch)
    (tmp_path / "files").mkdir()
    (tmp_path / "files" / "0000_a.lnk").write_bytes(b"x")
    data = {"schema": 1, "entries": [
        {"op": "modify", "path": str(desktop / "a.lnk"), "backup": "0000_a.lnk"},
        {"op": "rename", "path": str(desktop / "b.lnk"),
         "new_path": str(desktop / "\u00a0.lnk"), "backup": "0000_a.lnk"},
    ]}
    entries = validate_manifest(data, str(tmp_path))
    assert len(entries) == 2


def test_validate_manifest_rejects_outside_path(tmp_path, monkeypatch):
    _desktop(tmp_path, monkeypatch)
    (tmp_path / "files").mkdir()
    data = {"schema": 1, "entries": [
        {"op": "delete", "path": r"C:\Windows\System32\evil.dll", "backup": "x"},
    ]}
    with pytest.raises(BackupError):
        validate_manifest(data, str(tmp_path))


def test_validate_manifest_rejects_bad_schema(tmp_path):
    with pytest.raises(BackupError):
        validate_manifest({"schema": 99, "entries": []}, str(tmp_path))
    with pytest.raises(BackupError):
        validate_manifest({"schema": 1}, str(tmp_path))
    with pytest.raises(BackupError):
        validate_manifest([], str(tmp_path))


def test_create_backup_copies_files(tmp_path, monkeypatch):
    desktop = _desktop(tmp_path, monkeypatch)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    victim = desktop / "old.lnk"
    victim.write_bytes(b"original")
    cfg = {"persist_key": "T_Key"}
    create_backup(cfg, [{"op": "delete", "path": str(victim)}])
    manifest = json.loads((tmp_path / "appdata" / "Icons_Engine" / "backups" / "T_Key"
                           ).glob("*/manifest.json").__next__().read_text(encoding="utf-8"))
    assert manifest["schema"] == 1
    assert manifest["entries"][0]["op"] == "delete"
    copied = list((tmp_path / "appdata").rglob("0000_old.lnk"))
    assert copied and copied[0].read_bytes() == b"original"
