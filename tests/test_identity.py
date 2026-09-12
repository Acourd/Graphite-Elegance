from icon_engine import (
    _icon_file_from_raw,
    _key_from_icon_path,
    _read_url,
    _resolve_lnk,
    _same_icon_location,
    shortcut_identity,
)


class FakeShortcut:
    def __init__(self, target="", args="", wd=""):
        self.TargetPath = target
        self.Arguments = args
        self.WorkingDirectory = wd


class FakeShell:
    def __init__(self, mapping):
        self.mapping = mapping

    def CreateShortcut(self, path):
        return self.mapping[path]


def test_lnk_identity_includes_args_and_cwd():
    shell = FakeShell({
        "a.lnk": FakeShortcut(r"C:\Games\game.exe", "--profile A", r"C:\A"),
        "b.lnk": FakeShortcut(r"C:\Games\game.exe", "--profile B", r"C:\A"),
        "c.lnk": FakeShortcut(r"C:\Games\game.exe", "--profile A", r"C:\B"),
        "d.lnk": FakeShortcut(r"C:\Games\game.exe", "--profile A", r"C:\A"),
    })
    ident_a = shortcut_identity(shell, "a.lnk")
    assert ident_a == shortcut_identity(shell, "d.lnk")   # truly identical
    assert ident_a != shortcut_identity(shell, "b.lnk")   # different args
    assert ident_a != shortcut_identity(shell, "c.lnk")   # different cwd


def test_lnk_identity_path_case_insensitive_but_args_case_sensitive():
    same = FakeShell({
        "a.lnk": FakeShortcut(r"C:\Games\Game.EXE", "--profile A", r"C:\A"),
        "b.lnk": FakeShortcut(r"c:\games\game.exe", "--profile A", r"c:\a"),
    })
    # Windows paths are case-insensitive -> identical.
    assert shortcut_identity(same, "a.lnk") == shortcut_identity(same, "b.lnk")

    diff = FakeShell({
        "a.lnk": FakeShortcut(r"C:\Games\game.exe", "--Profile A", r"C:\A"),
        "b.lnk": FakeShortcut(r"C:\Games\game.exe", "--profile a", r"C:\A"),
    })
    # Arguments are case-sensitive -> must not be conflated.
    assert shortcut_identity(diff, "a.lnk") != shortcut_identity(diff, "b.lnk")


def test_url_identity_steam_normalized(tmp_path):
    f1 = tmp_path / "one.url"
    f1.write_text("[InternetShortcut]\nURL=steam://rungameid/730\n", encoding="utf-8")
    f2 = tmp_path / "two.url"
    f2.write_text("[InternetShortcut]\nURL=steam://rungameid/730/\n", encoding="utf-8")
    assert shortcut_identity(None, str(f1)) == shortcut_identity(None, str(f2))


def test_url_identity_plain(tmp_path):
    f = tmp_path / "web.url"
    f.write_text("[InternetShortcut]\nURL=https://example.com/x\n", encoding="utf-8")
    assert shortcut_identity(None, str(f)) == "url|https://example.com/x"


# --- regression: .url encoded in UTF-16 / legacy encodings ------------------
def test_url_identity_utf16(tmp_path):
    f = tmp_path / "u16.url"
    f.write_bytes("[InternetShortcut]\nURL=https://example.com/x\n".encode("utf-16"))
    assert shortcut_identity(None, str(f)) == "url|https://example.com/x"


def test_read_url_detects_utf16(tmp_path):
    f = tmp_path / "u16b.url"
    f.write_bytes("URL=https://a/\n".encode("utf-16"))
    lines, encoding = _read_url(str(f))
    assert encoding == "utf-16"
    assert any("https://a/" in line for line in lines)


def test_read_url_falls_back_to_cp1252(tmp_path):
    f = tmp_path / "ansi.url"
    f.write_bytes("URL=https://example.com/caf\xe9\n".encode("latin-1"))
    lines, encoding = _read_url(str(f))
    assert encoding == "cp1252"
    assert any("caf\xe9" in line for line in lines)


def test_icon_file_from_raw():
    assert _icon_file_from_raw(r"C:\a\Chrome.ico,0") == r"C:\a\Chrome.ico"
    assert _icon_file_from_raw(r'"C:\a\Chrome.ico",0') == r"C:\a\Chrome.ico"
    assert _icon_file_from_raw("") is None
    assert _icon_file_from_raw(None) is None


def test_icon_ref_with_comma_in_path():
    # The index is only the trailing ',<int>'; commas inside the path stay.
    assert _icon_file_from_raw(r"C:\a,b\Chrome.ico,0") == r"C:\a,b\Chrome.ico"
    assert _key_from_icon_path(r"C:\a,b\Chrome.ico,0") == "chrome"
    assert _icon_file_from_raw(r"C:\a,b\Chrome.ico") == r"C:\a,b\Chrome.ico"


def test_icon_ref_index_with_whitespace():
    # Common Windows form: 'path, 0' with a space (or tab) before the index.
    assert _icon_file_from_raw(r"C:\a\Chrome.ico, 0") == r"C:\a\Chrome.ico"
    assert _key_from_icon_path(r"C:\a\Chrome.ico, 0") == "chrome"
    assert _icon_file_from_raw("C:\\a\\Chrome.ico,\t0") == "C:\\a\\Chrome.ico"
    assert _key_from_icon_path('"C:\\a\\Chrome.ico", 0') == "chrome"


def test_url_identity_case_sensitive(tmp_path):
    f1 = tmp_path / "a.url"
    f1.write_text("[InternetShortcut]\nURL=https://example.com/Case\n", encoding="utf-8")
    f2 = tmp_path / "b.url"
    f2.write_text("[InternetShortcut]\nURL=https://example.com/case\n", encoding="utf-8")
    assert shortcut_identity(None, str(f1)) != shortcut_identity(None, str(f2))


# --- regression: re-applying the same theme must be a no-op -----------------
def test_same_icon_location_normalizes_windows_form():
    assert _same_icon_location(r"C:\a\X.ico,0", r"C:\A\x.ico", ".lnk")
    assert _same_icon_location(r"C:\a\X.ico, 0", r"C:\a\X.ico", ".lnk")
    assert _same_icon_location(r"C:\a\X.ico", r"C:\a\X.ico", ".lnk")
    assert not _same_icon_location(r"C:\a\X.ico,1", r"C:\a\X.ico", ".lnk")
    assert not _same_icon_location(r"C:\b\X.ico,0", r"C:\a\X.ico", ".lnk")
    assert not _same_icon_location("", r"C:\a\X.ico", ".lnk")
    assert _same_icon_location(r"C:\a\X.ico", r"C:\a\X.ico", ".url")


# --- regression: generic executable stems must not steal icon matches -------
class _SC:
    def __init__(self, target, icon=""):
        self.TargetPath = target
        self.IconLocation = icon
        self.Arguments = ""
        self.WorkingDirectory = ""


def test_resolve_lnk_skips_generic_target_stems():
    available = {"update": r"C:\icons\Update.ico", "discord": r"C:\icons\Discord.ico"}
    assert _resolve_lnk(_SC(r"C:\Apps\Update.exe"), "x.lnk", available) is None


def test_resolve_lnk_matches_specific_target_stems():
    available = {"ccleaner": r"C:\icons\Ccleaner.ico"}
    assert _resolve_lnk(_SC(r"C:\Program Files\CCleaner\CCleaner.exe"),
                        "CCleaner 7.lnk", available) == r"C:\icons\Ccleaner.ico"
