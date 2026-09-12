import json
import os
import time

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
    digest = "0" * 64
    data = {"schema": 2, "entries": [
        {"op": "modify", "path": str(desktop / "a.lnk"), "backup": "0000_a.lnk",
         "sha256": digest},
        {"op": "rename", "path": str(desktop / "b.lnk"),
         "new_path": str(desktop / "\u00a0.lnk"), "backup": "0000_a.lnk",
         "sha256": digest},
    ]}
    entries = validate_manifest(data, str(tmp_path))
    assert len(entries) == 2


def test_validate_manifest_rejects_missing_hashes(tmp_path, monkeypatch):
    desktop = _desktop(tmp_path, monkeypatch)
    (tmp_path / "files").mkdir()
    data = {"schema": 2, "entries": [
        {"op": "modify", "path": str(desktop / "a.lnk"), "backup": "0000_a.lnk"},
    ]}
    with pytest.raises(BackupError):
        validate_manifest(data, str(tmp_path))


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
    assert manifest["schema"] == 2
    assert manifest["entries"][0]["op"] == "delete"
    assert len(manifest["entries"][0]["sha256"]) == 64
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


def test_restore_is_all_or_nothing_on_copy_failure(tmp_path, monkeypatch):
    import icon_engine

    desktop = _desktop(tmp_path, monkeypatch)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    first = desktop / "a.lnk"
    second = desktop / "b.lnk"
    first.write_bytes(b"A0")
    second.write_bytes(b"B0")
    backup = create_backup({"persist_key": "T_Key"},
                           [{"op": "modify", "path": str(first)},
                            {"op": "modify", "path": str(second)}])
    first.write_bytes(b"A1")
    second.write_bytes(b"B1")

    real_copy2 = icon_engine.shutil.copy2
    calls = {"n": 0}

    def flaky(src, dst, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("fallo de I/O")
        return real_copy2(src, dst, *args, **kwargs)

    monkeypatch.setattr(icon_engine.shutil, "copy2", flaky)
    with pytest.raises(BackupError):
        restore_backup(backup, dry_run=False)
    # Staging fails before any destination is replaced.
    assert first.read_bytes() == b"A1"
    assert second.read_bytes() == b"B1"


def test_restore_keeps_foreign_file_at_renamed_destination(tmp_path, monkeypatch):
    desktop = _desktop(tmp_path, monkeypatch)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    original = desktop / "a.lnk"
    hidden = desktop / "\u00a0.lnk"
    original.write_bytes(b"original")
    backup = create_backup({"persist_key": "T_Key"},
                           [{"op": "rename", "path": str(original), "new_path": str(hidden)}])
    os.replace(original, hidden)
    hidden.write_bytes(b"user content")  # the user replaced the renamed shortcut

    assert restore_backup(backup, dry_run=False) == 1
    assert hidden.read_bytes() == b"user content"  # never deleted
    assert not original.exists()
    assert not list(desktop.glob("*.isoform-restore-*"))


def test_restore_rolls_back_when_a_later_replace_fails(tmp_path, monkeypatch):
    import icon_engine

    desktop = _desktop(tmp_path, monkeypatch)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    first = desktop / "a.lnk"
    second = desktop / "b.lnk"
    first.write_bytes(b"A0")
    second.write_bytes(b"B0")
    backup = create_backup({"persist_key": "T_Key"},
                           [{"op": "modify", "path": str(first)},
                            {"op": "modify", "path": str(second)}])
    first.write_bytes(b"A1")
    second.write_bytes(b"B1")

    real_replace = os.replace
    state = {"failed": False}

    def flaky(src, dst, *args, **kwargs):
        if not state["failed"] and os.path.abspath(dst) == str(second):
            state["failed"] = True
            raise OSError("locked")
        return real_replace(src, dst, *args, **kwargs)

    monkeypatch.setattr(icon_engine.os, "replace", flaky)
    assert restore_backup(backup, dry_run=False) == 1
    assert first.read_bytes() == b"A1"
    assert second.read_bytes() == b"B1"
    assert not list(desktop.glob("*.isoform-restore-*"))


def test_restore_detects_corrupted_restored_bytes(tmp_path, monkeypatch):
    import icon_engine

    desktop = _desktop(tmp_path, monkeypatch)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    victim = desktop / "a.lnk"
    victim.write_bytes(b"A0")
    backup = create_backup({"persist_key": "T_Key"}, [{"op": "modify", "path": str(victim)}])
    victim.write_bytes(b"A1")

    real_copy2 = icon_engine.shutil.copy2

    def corrupted(src, dst, *args, **kwargs):
        real_copy2(src, dst, *args, **kwargs)
        if os.path.basename(os.path.dirname(src)) == "files":
            with open(dst, "ab") as fh:
                fh.write(b"X")

    monkeypatch.setattr(icon_engine.shutil, "copy2", corrupted)
    assert restore_backup(backup, dry_run=False) == 1
    assert victim.read_bytes() == b"A1"
    assert not list(desktop.glob("*.isoform-restore-*"))


# --- regression: orphan sweep must be strict, scoped and age-limited --------
def test_orphan_sweep_is_strict_and_age_limited(tmp_path, monkeypatch):
    import icon_engine

    desktop = _desktop(tmp_path, monkeypatch)
    outside = tmp_path / "Elsewhere"
    outside.mkdir()

    stale = desktop / "Chrome.url.isoform-restore-deadbeef"
    recent = desktop / "Chrome.url.isoform-restore-00000001"
    wrong_name = desktop / "notes.txt"
    outside_stale = outside / "Other.url.isoform-restore-deadbeef"
    for path in (stale, recent, wrong_name, outside_stale):
        path.write_bytes(b"x")
    old = time.time() - 3600
    os.utime(stale, (old, old))
    os.utime(outside_stale, (old, old))

    assert icon_engine.sweep_restore_orphans() == 1
    assert not stale.exists()          # stale orphan removed
    assert recent.exists()             # recent temp kept (active restore safety)
    assert wrong_name.exists()         # non-matching name kept
    assert outside_stale.exists()      # outside the Desktop roots: untouched


def test_restore_sweeps_stale_orphans(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    desktop = _desktop(tmp_path, monkeypatch)
    victim = desktop / "a.lnk"
    victim.write_bytes(b"original")
    backup = create_backup({"persist_key": "T_Key"}, [{"op": "modify", "path": str(victim)}])

    orphan = desktop / "old.lnk.isoform-restore-cafebabe"
    orphan.write_bytes(b"stale")
    old = time.time() - 3600
    os.utime(orphan, (old, old))

    assert restore_backup(backup, dry_run=False) == 0
    assert not orphan.exists()
    assert victim.read_bytes() == b"original"
