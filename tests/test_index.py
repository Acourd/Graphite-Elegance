import os

import pytest

from icon_engine import IconNameError, index_icons


def _touch(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(b"\x00")


def test_index_unique_names(tmp_path):
    _touch(str(tmp_path / "A" / "Chrome.ico"))
    _touch(str(tmp_path / "B" / "Discord.ico"))
    index = index_icons(str(tmp_path))
    assert "chrome" in index
    assert "discord" in index


def test_index_collision_raises(tmp_path):
    _touch(str(tmp_path / "A" / "Chrome.ico"))
    _touch(str(tmp_path / "B" / "Chrome.ico"))
    with pytest.raises(IconNameError):
        index_icons(str(tmp_path))


def test_index_collision_allowed(tmp_path):
    _touch(str(tmp_path / "A" / "Chrome.ico"))
    _touch(str(tmp_path / "B" / "Chrome.ico"))
    index = index_icons(str(tmp_path), allow_duplicates=True)
    assert "chrome" in index


def test_space_insensitive_collision(tmp_path):
    _touch(str(tmp_path / "A" / "Minecraft V2.ico"))
    _touch(str(tmp_path / "B" / "MinecraftV2.ico"))
    with pytest.raises(IconNameError):
        index_icons(str(tmp_path))
