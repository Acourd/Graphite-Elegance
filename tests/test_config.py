import json

import pytest

from icon_engine import ConfigError, load_config, validate_config


def cfg(**kw):
    base = {"name": "Demo", "persist_key": "Demo_Key", "icons_dir": "Icons/ICO"}
    base.update(kw)
    return base


def test_valid_config_resolves_paths(tmp_path):
    resolved = validate_config(cfg(), str(tmp_path / "theme.json"))
    assert resolved["persist_key"] == "Demo_Key"
    assert resolved["icons_path"] == str(tmp_path / "Icons" / "ICO")


@pytest.mark.parametrize("bad", [
    {"name": ""},
    {"name": 5},
    {"persist_key": ""},
    {"persist_key": "../evil"},
    {"persist_key": "a/b"},
    {"persist_key": ".."},
    {"persist_key": "bad key"},
    {"icons_dir": ""},
    {"icons_dir": "C:/abs/path"},
    {"icons_dir": "../outside"},
    {"order": "not-a-list"},
    {"order": [1, 2]},
])
def test_invalid_config_rejected(bad, tmp_path):
    with pytest.raises(ConfigError):
        validate_config(cfg(**bad), str(tmp_path / "theme.json"))


def test_load_config_missing_file(tmp_path):
    with pytest.raises(ConfigError):
        load_config(str(tmp_path / "nope.json"))


def test_load_config_invalid_json(tmp_path):
    p = tmp_path / "theme.json"
    p.write_text("{ not json", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(str(p))


def test_load_config_ok(tmp_path):
    p = tmp_path / "theme.json"
    p.write_text(json.dumps(cfg()), encoding="utf-8")
    resolved = load_config(str(p))
    assert resolved["name"] == "Demo"
