import json
import os
import struct
import zlib

from icon_validate import _rel, read_ico_sizes, validate_config


def _bmp_payload(size):
    stride = size * 4
    size_image = stride * size * 2  # XOR + AND, like Pillow
    header = struct.pack("<IiiHHIIiiII", 40, size, size * 2, 1, 32, 0,
                         size_image, 0, 0, 0, 0)
    return header + b"\x00" * size_image


def _png_chunk(ctype, body):
    crc = zlib.crc32(ctype + body) & 0xffffffff
    return struct.pack(">I", len(body)) + ctype + body + struct.pack(">I", crc)


def _png_payload(w, h, corrupt=False):
    raw = b"\x00" * (h * (1 + w * 4))
    data = zlib.compress(b"junk" if corrupt else raw)
    return (b"\x89PNG\r\n\x1a\n"
            + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + _png_chunk(b"IDAT", data)
            + _png_chunk(b"IEND", b""))


def make_ico(sizes, png=False, corrupt=False):
    count = len(sizes)
    offset = 6 + count * 16
    entries = b""
    data = b""
    for s in sizes:
        w = 0 if s == 256 else s
        if png:
            payload = _png_payload(s, s, corrupt=corrupt)
        else:
            payload = _bmp_payload(s)
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


# --- deep payload validation -------------------------------------------------
def test_validate_rejects_empty_icons_dir(tmp_path):
    d = tmp_path / "Theme_Release"
    (d / "Icons" / "ICO").mkdir(parents=True)
    (d / "theme.json").write_text(json.dumps(
        {"name": "Demo", "persist_key": "Demo_Key", "icons_dir": "Icons/ICO"}),
        encoding="utf-8")
    result = validate_config(str(d / "theme.json"))
    assert any("no contiene" in e for e in result["errors"])


def test_read_ico_sizes_accepts_valid_png_frame(tmp_path):
    p = tmp_path / "png.ico"
    p.write_bytes(make_ico([256], png=True))
    sizes, err = read_ico_sizes(str(p))
    assert sizes == [256] and err is None


def test_read_ico_sizes_rejects_corrupt_png_idat(tmp_path):
    p = tmp_path / "bad.ico"
    p.write_bytes(make_ico([256], png=True, corrupt=True))
    sizes, err = read_ico_sizes(str(p))
    assert sizes == [256] and err is not None


def test_read_ico_sizes_rejects_bad_png_crc(tmp_path):
    size = 256
    raw = b"\x00" * (size * (1 + size * 4))
    bad_crc = (zlib.crc32(b"IDAT" + zlib.compress(raw)) + 1) & 0xffffffff
    payload = (b"\x89PNG\r\n\x1a\n"
               + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
               + struct.pack(">I", len(zlib.compress(raw))) + b"IDAT" + zlib.compress(raw)
               + struct.pack(">I", bad_crc)
               + _png_chunk(b"IEND", b""))
    ico = (struct.pack("<HHH", 0, 1, 1)
           + struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(payload), 22)
           + payload)
    p = tmp_path / "crc.ico"
    p.write_bytes(ico)
    sizes, err = read_ico_sizes(str(p))
    assert sizes == [256] and err is not None
    assert "CRC" in err


def _single_frame_ico(payload):
    return (struct.pack("<HHH", 0, 1, 1)
            + struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(payload), 22)
            + payload)


def test_read_ico_sizes_rejects_png_without_idat(tmp_path):
    payload = (b"\x89PNG\r\n\x1a\n"
               + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 256, 256, 8, 6, 0, 0, 0))
               + _png_chunk(b"IEND", b""))
    p = tmp_path / "noidat.ico"
    p.write_bytes(_single_frame_ico(payload))
    sizes, err = read_ico_sizes(str(p))
    assert sizes == [256] and err is not None
    assert "IDAT" in err


def test_read_ico_sizes_rejects_interlaced_png(tmp_path):
    raw = b"\x00" * (256 * (1 + 256 * 4))
    payload = (b"\x89PNG\r\n\x1a\n"
               + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 256, 256, 8, 6, 0, 0, 1))
               + _png_chunk(b"IDAT", zlib.compress(raw))
               + _png_chunk(b"IEND", b""))
    p = tmp_path / "interlaced.ico"
    p.write_bytes(_single_frame_ico(payload))
    sizes, err = read_ico_sizes(str(p))
    assert sizes == [256] and err is not None
    assert "entrelazado" in err


def test_read_ico_sizes_rejects_invalid_png_filter(tmp_path):
    raw = (b"\x05" + b"\x00" * (256 * 4)) * 256
    payload = (b"\x89PNG\r\n\x1a\n"
               + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 256, 256, 8, 6, 0, 0, 0))
               + _png_chunk(b"IDAT", zlib.compress(raw))
               + _png_chunk(b"IEND", b""))
    p = tmp_path / "filter.ico"
    p.write_bytes(_single_frame_ico(payload))
    sizes, err = read_ico_sizes(str(p))
    assert sizes == [256] and err is not None
    assert "filtro" in err


def test_read_ico_sizes_rejects_invalid_ihdr_combo(tmp_path):
    payload = (b"\x89PNG\r\n\x1a\n"
               + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 256, 256, 4, 2, 0, 0, 0))
               + _png_chunk(b"IDAT", zlib.compress(b"\x00" * 64))
               + _png_chunk(b"IEND", b""))
    p = tmp_path / "combo.ico"
    p.write_bytes(_single_frame_ico(payload))
    sizes, err = read_ico_sizes(str(p))
    assert sizes == [256] and err is not None
    assert "IHDR" in err


# --- regression: relpath across Windows drives (C: repo vs D: tmp) ---------
def test_rel_falls_back_to_absolute_across_drives(monkeypatch):
    import icon_validate

    def _boom(path, start=None):
        raise ValueError("path is on mount 'C:', start on mount 'D:'")

    monkeypatch.setattr(icon_validate.os.path, "relpath", _boom)
    out = _rel(r"C:\tmp\Theme\Chrome.ico", r"D:\repo")
    assert os.path.isabs(out)
    assert out.endswith("Chrome.ico")
