import os
import shutil

from icon_engine import _publish_icons, _published_icons_dir


def _theme_dir(tmp_path):
    src = tmp_path / "Theme_Release" / "Icons" / "ICO"
    src.mkdir(parents=True)
    (src / "Chrome.ico").write_bytes(b"new")
    return src


def test_publish_replaces_after_a_full_copy(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    src = _theme_dir(tmp_path)
    cfg = {"persist_key": "T_Key", "icons_path": str(src)}
    dest = _publish_icons(cfg)
    assert dest == _published_icons_dir(cfg)
    assert os.path.isfile(os.path.join(dest, "Chrome.ico"))


def test_publish_failure_keeps_existing_destination(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    src = _theme_dir(tmp_path)
    cfg = {"persist_key": "T_Key", "icons_path": str(src)}

    dest = _published_icons_dir(cfg)
    os.makedirs(dest)
    sentinel = os.path.join(dest, "OLD.ico")
    with open(sentinel, "wb") as fh:
        fh.write(b"old")

    def boom(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(shutil, "copytree", boom)
    returned = _publish_icons(cfg)

    # The previously published tree must survive a failed copy, and we fall
    # back to the source icons instead.
    assert os.path.isfile(sentinel)
    assert returned == cfg["icons_path"]
    assert not any(".staging-" in n for n in os.listdir(os.path.dirname(dest)))
