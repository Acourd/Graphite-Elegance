import json
import os

import pytest

from icon_engine import (
    BackupError,
    _backup_base,
    _safe_backup_file,
    appdata_dir,
    create_backup,
    desktop_dirs,
    is_within,
    restore_backup,
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


# --- regression: environment lookups must not be eager / Windows-only -------
def test_backup_base_does_not_require_userprofile(tmp_path, monkeypatch):
    # Before the fix, LOCALAPPDATA's default argument evaluated USERPROFILE
    # eagerly and raised KeyError on Linux even when LOCALAPPDATA was set.
    monkeypatch.delenv("USERPROFILE", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    base = _backup_base({"persist_key": "T_Key"})
    assert base.startswith(str(tmp_path / "appdata"))


def test_appdata_dir_falls_back_without_userprofile(monkeypatch):
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.delenv("USERPROFILE", raising=False)
    assert appdata_dir()  # must not raise


def test_desktop_dirs_without_userprofile(monkeypatch):
    monkeypatch.delenv("ISO_DESKTOP_DIRS", raising=False)
    monkeypatch.delenv("USERPROFILE", raising=False)
    dirs = desktop_dirs()
    assert dirs and all(isinstance(d, str) for d in dirs)


# --- regression: two runs in the same second must not share a backup dir ----
def test_backups_are_unique_within_same_second(tmp_path, monkeypatch):
    desktop = _desktop(tmp_path, monkeypatch)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    victim = desktop / "a.lnk"
    victim.write_bytes(b"x")
    cfg = {"persist_key": "T_Key"}
    first = create_backup(cfg, [{"op": "delete", "path": str(victim)}])
    second = create_backup(cfg, [{"op": "delete", "path": str(victim)}])
    assert first != second
    assert os.path.isfile(os.path.join(first, "manifest.json"))
    assert os.path.isfile(os.path.join(second, "manifest.json"))


# --- regression: restore must pre-validate and must not need pywin32 --------
def test_restore_prevalidates_all_backup_files(tmp_path, monkeypatch):
    desktop = _desktop(tmp_path, monkeypatch)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    victim = desktop / "a.lnk"
    victim.write_bytes(b"original")
    backup = create_backup({"persist_key": "T_Key"}, [{"op": "modify", "path": str(victim)}])
    # Corrupt the backup: remove the copied file so the manifest points nowhere.
    for copied in (tmp_path / "appdata").rglob("0000_a.lnk"):
        copied.unlink()

    with pytest.raises(BackupError):
        restore_backup(backup, dry_run=False)
    assert victim.read_bytes() == b"original"  # nothing was half-restored


def test_restore_does_not_require_pywin32(tmp_path, monkeypatch):
    import icon_engine

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    desktop = _desktop(tmp_path, monkeypatch)
    victim = desktop / "a.lnk"
    victim.write_bytes(b"original")
    backup = create_backup({"persist_key": "T_Key"}, [{"op": "modify", "path": str(victim)}])
    victim.write_bytes(b"changed")

    def no_com():
        raise icon_engine.DependencyError("pywin32 no disponible")

    monkeypatch.setattr(icon_engine, "_com", no_com)
    assert restore_backup(backup, dry_run=False) == 0
    assert victim.read_bytes() == b"original"
