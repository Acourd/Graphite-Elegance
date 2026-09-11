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

