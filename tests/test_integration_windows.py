import glob
import json
import os
import struct
import sys

import pytest

from icon_engine import apply_theme, load_config, organize_desktop, restore_backup

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows + COM only")


def make_ico(sizes):
    count = len(sizes)
    offset = 6 + count * 16
    entries = b""
    data = b""
    for s in sizes:
        w = 0 if s == 256 else s
        payload = b"\x28\x00\x00\x00" + b"\x00" * 8  # valid BITMAPINFOHEADER start
        entries += struct.pack("<BBBBHHII", w, w, 0, 0, 1, 32, len(payload), offset)
        offset += len(payload)
        data += payload
    return struct.pack("<HHH", 0, 1, count) + entries + data


@pytest.fixture
def world(tmp_path, monkeypatch):
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    monkeypatch.setenv("ISO_DESKTOP_DIRS", str(desktop))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))

    theme = tmp_path / "Theme_Release"
    icons = theme / "Icons" / "ICO"
    icons.mkdir(parents=True)
    (theme / "theme.json").write_text(
        json.dumps({"name": "Test Theme", "persist_key": "Test_Key", "icons_dir": "Icons/ICO"}),
        encoding="utf-8")
    (icons / "Chrome.ico").write_bytes(make_ico([16, 32, 48, 64, 128, 256]))
    return desktop, load_config(str(theme / "theme.json"))


def _url(name, url):
    return f"[InternetShortcut]\nURL={url}\nIconFile=http://x/y.ico\nIconIndex=0\n"


def test_apply_backup_and_restore(world):
    desktop, cfg = world
    (desktop / "Chrome.url").write_text(_url("Chrome", "https://example.com/"), encoding="utf-8")

    assert apply_theme(cfg, yes=True, rename=True, cleanup=False) == 0

    files = os.listdir(desktop)
    assert len(files) == 1
    assert all(ch == "\u00a0" for ch in os.path.splitext(files[0])[0])

    backups = glob.glob(str(desktop.parent / "appdata" / "Icons_Engine" / "backups" / "Test_Key" / "*"))
    assert backups, "no se creó backup"

    assert restore_backup(backups[0], dry_run=False) == 0
    assert (desktop / "Chrome.url").is_file()
    assert not any(f.startswith("\u00a0") for f in os.listdir(desktop))


def test_apply_repairs_published_tree_without_shortcut_changes(world):
    from icon_engine import _published_icons_dir

    desktop, cfg = world
    (desktop / "Chrome.url").write_text(_url("Chrome", "https://example.com/"), encoding="utf-8")
    assert apply_theme(cfg, yes=True, rename=False, cleanup=False) == 0

    published = _published_icons_dir(cfg)
    icon = os.path.join(published, "Chrome.ico")
    assert os.path.isfile(icon)
    os.remove(icon)
    obsolete = os.path.join(published, "Obsolete.ico")
    with open(obsolete, "wb") as fh:
        fh.write(b"gone")

    backups_root = str(desktop.parent / "appdata" / "Icons_Engine" / "backups" / "Test_Key")
    before = set(glob.glob(os.path.join(backups_root, "*")))

    assert apply_theme(cfg, yes=True, rename=False, cleanup=False) == 0
    assert os.path.isfile(icon), "la publicación dañada debe repararse"
    assert not os.path.exists(obsolete), "los iconos obsoletos deben retirarse"
    after = set(glob.glob(os.path.join(backups_root, "*")))
    assert after == before, "republicar no debe crear backups"


def test_failed_rename_cannot_authorize_deleting_decoy(world, monkeypatch):
    import icon_engine

    desktop, cfg = world
    (desktop / "Chrome.url").write_text(_url("Chrome", "https://example.com/"), encoding="utf-8")
    stolen = {}

    real_rename = os.rename

    def flaky(src, dst, *args, **kwargs):
        if os.path.basename(dst).startswith("\u00a0"):
            with open(dst, "wb") as fh:
                fh.write(b"foreign")
            stolen["path"] = dst
            raise FileExistsError("collision")
        return real_rename(src, dst, *args, **kwargs)

    monkeypatch.setattr(icon_engine.os, "rename", flaky)
    assert apply_theme(cfg, yes=True, rename=True, cleanup=False) == 1
    assert stolen.get("path") and os.path.isfile(stolen["path"])

    backups = glob.glob(str(desktop.parent / "appdata" / "Icons_Engine" / "backups" / "Test_Key" / "*"))
    assert backups
    with open(os.path.join(backups[0], "manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    rename_entries = [e for e in manifest["entries"] if e["op"] == "rename"]
    assert rename_entries
    assert not any("post_sha256" in e for e in rename_entries)

    assert restore_backup(backups[0], dry_run=False) == 1
    with open(stolen["path"], "rb") as fh:
        assert fh.read() == b"foreign"


def test_organize_records_post_hash_for_restore(world):
    desktop, cfg = world
    (desktop / "Chrome.url").write_text(_url("Chrome", "https://example.com/"), encoding="utf-8")
    assert apply_theme(cfg, yes=True, rename=False, cleanup=False) == 0
    assert organize_desktop(cfg, yes=True) == 0
    invisible = [f for f in os.listdir(desktop) if f.startswith("\u00a0")]
    assert len(invisible) == 1

    backups = glob.glob(str(desktop.parent / "appdata" / "Icons_Engine" / "backups" / "Test_Key" / "*"))
    rename_backups = []
    for path in backups:
        with open(os.path.join(path, "manifest.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        if any(e.get("op") == "rename" for e in data.get("entries", [])):
            rename_backups.append(path)
    assert rename_backups
    assert restore_backup(rename_backups[0], dry_run=False) == 0
    assert (desktop / "Chrome.url").is_file()
    assert not any(f.startswith("\u00a0") for f in os.listdir(desktop))


def test_rename_only_touches_theme_shortcuts(world):
    desktop, cfg = world
    (desktop / "Chrome.url").write_text(_url("Chrome", "https://example.com/"), encoding="utf-8")
    (desktop / "Other.url").write_text(_url("Other", "https://other.example/"), encoding="utf-8")

    # Chrome resolves to the theme icon; Other does not.
    assert apply_theme(cfg, yes=True, rename=True, cleanup=False) == 0

    assert (desktop / "Other.url").is_file(), "un acceso ajeno al tema no debe renombrarse"
    invisible = [f for f in os.listdir(desktop) if f.startswith("\u00a0")]
    assert len(invisible) == 1


def test_dry_run_creates_no_backup(world):
    desktop, cfg = world
    (desktop / "Chrome.url").write_text(_url("Chrome", "https://example.com/"), encoding="utf-8")
    before = (desktop / "Chrome.url").read_text(encoding="utf-8")
    assert apply_theme(cfg, dry_run=True, cleanup=True, rename=True) == 0
    assert (desktop / "Chrome.url").read_text(encoding="utf-8") == before
    backups_root = desktop.parent / "appdata" / "Icons_Engine" / "backups"
    assert not backups_root.exists(), "dry-run no debe crear backups"


def test_organize_ignores_non_theme_shortcuts(world, capsys):
    desktop, cfg = world
    (desktop / "Chrome.url").write_text(_url("Chrome", "https://example.com/"), encoding="utf-8")
    (desktop / "Other.url").write_text(_url("Other", "https://other.example/"), encoding="utf-8")
    # Apply first (no rename) so Chrome carries the theme icon.
    assert apply_theme(cfg, yes=True, rename=False, cleanup=False) == 0
    capsys.readouterr()
    assert organize_desktop(cfg, dry_run=True) == 0
    out = capsys.readouterr().out.lower()
    assert "chrome" in out
    assert "other" not in out


def test_organize_ignores_foreign_icon_path(world, capsys):
    # Same icon name, but the referenced file lives in another theme's tree.
    desktop, cfg = world
    other = desktop.parent / "Other_Release" / "Icons" / "ICO"
    other.mkdir(parents=True)
    source_icon = desktop.parent / "Theme_Release" / "Icons" / "ICO" / "Chrome.ico"
    (other / "Chrome.ico").write_bytes(source_icon.read_bytes())
    (desktop / "Chrome.url").write_text(
        "[InternetShortcut]\nURL=https://example.com/\n"
        f"IconFile={other / 'Chrome.ico'}\nIconIndex=0\n", encoding="utf-8")
    assert organize_desktop(cfg, dry_run=True) == 0
    assert "chrome" not in capsys.readouterr().out.lower()


def test_reapplying_is_idempotent(world, capsys):
    desktop, cfg = world
    (desktop / "Chrome.url").write_text(_url("Chrome", "https://example.com/"), encoding="utf-8")
    assert apply_theme(cfg, yes=True, rename=False, cleanup=False) == 0

    backups_root = desktop.parent / "appdata" / "Icons_Engine" / "backups" / "Test_Key"
    assert len(glob.glob(str(backups_root / "*"))) == 1
    capsys.readouterr()

    # Re-applying an already-published theme must be a no-op (no phantom change,
    # no extra backup, no shortcut rewrite).
    assert apply_theme(cfg, yes=True, rename=False, cleanup=False) == 0
    assert "nada que hacer" in capsys.readouterr().out.lower()
    assert len(glob.glob(str(backups_root / "*"))) == 1


def test_organize_twice_is_idempotent(world, capsys):
    desktop, cfg = world
    (desktop / "Chrome.url").write_text(_url("Chrome", "https://example.com/"), encoding="utf-8")
    assert apply_theme(cfg, yes=True, rename=False, cleanup=False) == 0
    capsys.readouterr()

    assert organize_desktop(cfg, dry_run=False, yes=True) == 0
    capsys.readouterr()
    # Everything is already invisible -> nothing left to organize.
    assert organize_desktop(cfg, dry_run=False, yes=True) == 0
    assert "no se encontraron" in capsys.readouterr().out.lower()


def test_apply_real_lnk_sets_icon_and_restore_recovers(world):
    import win32com.client

    desktop, cfg = world
    lnk = desktop / "Chrome.lnk"
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(str(lnk))
    shortcut.TargetPath = r"C:\Windows\System32\notepad.exe"
    shortcut.Arguments = "--profile A"
    shortcut.WorkingDirectory = r"C:\Windows"
    shortcut.Save()

    assert apply_theme(cfg, yes=True, rename=False, cleanup=False) == 0
    assert "Icons" in shell.CreateShortcut(str(lnk)).IconLocation

    backups = glob.glob(str(desktop.parent / "appdata" / "Icons_Engine" / "backups" / "Test_Key" / "*"))
    assert backups
    assert restore_backup(backups[0], dry_run=False) == 0
    # The original .lnk (no custom icon) is restored.
    assert "Icons" not in shell.CreateShortcut(str(lnk)).IconLocation

