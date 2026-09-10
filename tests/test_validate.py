import json
import struct

from icon_validate import read_ico_sizes, validate_config


def make_ico(sizes):
    count = len(sizes)
    offset = 6 + count * 16
    entries = b""
    data = b""
    for s in sizes:
        w = 0 if s == 256 else s
        payload = b"\x00\x00\x00\x00"
        entries += struct.pack("<BBBBHHII", w, w, 0, 0, 1, 32, len(payload), offset)
        offset += len(payload)
        data += payload
    return struct.pack("<HHH", 0, 1, count) + entries + data


def _write(path, sizes):
    with open(path, "wb") as fh:
        fh.write(make_ico(sizes))


def test_read_ico_sizes_maps_zero_to_256(tmp_path):
    p = tmp_path / "x.ico"
    _write(str(p), [16, 32, 48, 64, 128, 256])
    sizes, err = read_ico_sizes(str(p))
    assert err is None
    assert sizes == [16, 32, 48, 64, 128, 256]


def test_read_ico_sizes_rejects_garbage(tmp_path):
    p = tmp_path / "bad.ico"
    p.write_bytes(b"not an ico at all")
    sizes, err = read_ico_sizes(str(p))
    assert err is not None


def _theme(tmp_path, sizes, name="Demo", key="Demo_Key", dup=False):
    d = tmp_path / "Theme_Release"
    icons = d / "Icons" / "ICO"
    icons.mkdir(parents=True)
    (d / "theme.json").write_text(json.dumps(
        {"name": name, "persist_key": key, "icons_dir": "Icons/ICO"}), encoding="utf-8")
    _write(str(icons / "Chrome.ico"), sizes)
    if dup:
        cat = icons / "Sub"
        cat.mkdir()
        _write(str(cat / "Chrome.ico"), sizes)
    return d / "theme.json"


def test_validate_complete_passes(tmp_path):
    cfg = _theme(tmp_path, [16, 32, 48, 64, 128, 256])
    result = validate_config(str(cfg))
    assert result["errors"] == []


def test_validate_incomplete_fails(tmp_path):
    cfg = _theme(tmp_path, [256])
    result = validate_config(str(cfg))
    assert result["errors"]
    assert any("faltan" in e for e in result["errors"])


def test_validate_duplicate_names_fail(tmp_path):
    cfg = _theme(tmp_path, [16, 32, 48, 64, 128, 256], dup=True)
    result = validate_config(str(cfg))
    assert any("duplicad" in e.lower() for e in result["errors"])


def test_validate_baseline_downgrades(tmp_path):
    cfg = _theme(tmp_path, [256])
    result = validate_config(str(cfg), baseline=["*Chrome.ico"])
    assert result["errors"] == []
    assert any("baseline" in w for w in result["warnings"])
