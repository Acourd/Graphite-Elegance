from icon_engine import shortcut_identity


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


def test_lnk_identity_case_insensitive():
    shell = FakeShell({
        "a.lnk": FakeShortcut(r"C:\Games\Game.EXE", "--Profile A", r"C:\A"),
        "b.lnk": FakeShortcut(r"c:\games\game.exe", "--profile a", r"c:\a"),
    })
    assert shortcut_identity(shell, "a.lnk") == shortcut_identity(shell, "b.lnk")


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
