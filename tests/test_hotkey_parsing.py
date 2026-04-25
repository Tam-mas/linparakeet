"""parse_key / key_matches behaviour without touching pynput's listener thread."""
import sys
import types


# Stub pynput.keyboard so the test runs without a real X server.
class _Key:
    """Sentinel objects standing in for keyboard.Key.* members."""
    def __init__(self, name: str) -> None:
        self.name = name

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Key) and other.name == self.name

    def __hash__(self) -> int:
        return hash(self.name)


class _KeyCode:
    def __init__(self, char: str) -> None:
        self.char = char

    @classmethod
    def from_char(cls, c: str) -> "_KeyCode":
        return cls(c)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _KeyCode) and other.char == self.char


class _KeyEnum:
    ctrl_r = _Key("ctrl_r")
    ctrl_l = _Key("ctrl_l")
    ctrl = _Key("ctrl")
    alt_r = _Key("alt_r")
    alt_l = _Key("alt_l")
    alt = _Key("alt")
    shift_r = _Key("shift_r")
    shift_l = _Key("shift_l")
    shift = _Key("shift")
    space = _Key("space")
    tab = _Key("tab")
    caps_lock = _Key("caps_lock")
    f1 = _Key("f1")
    f2 = _Key("f2")
    f3 = _Key("f3")
    f4 = _Key("f4")
    f5 = _Key("f5")
    f6 = _Key("f6")
    f7 = _Key("f7")
    f8 = _Key("f8")
    f9 = _Key("f9")
    f10 = _Key("f10")
    f11 = _Key("f11")
    f12 = _Key("f12")
    esc = _Key("esc")


pynput_mod = types.ModuleType("pynput")
keyboard_mod = types.ModuleType("pynput.keyboard")
keyboard_mod.Key = _KeyEnum
keyboard_mod.KeyCode = _KeyCode
keyboard_mod.Listener = object  # never instantiated in these tests
pynput_mod.keyboard = keyboard_mod
sys.modules["pynput"] = pynput_mod
sys.modules["pynput.keyboard"] = keyboard_mod

from app import hotkey  # noqa: E402


def test_parse_named_keys() -> None:
    assert hotkey.parse_key("right ctrl") is _KeyEnum.ctrl_r
    assert hotkey.parse_key("Left Ctrl") is _KeyEnum.ctrl_l  # case-insensitive
    assert hotkey.parse_key("f9") is _KeyEnum.f9


def test_parse_single_character_falls_through_to_keycode() -> None:
    parsed = hotkey.parse_key("a")
    assert isinstance(parsed, _KeyCode)
    assert parsed.char == "a"


def test_parse_unknown_falls_back_to_right_ctrl() -> None:
    assert hotkey.parse_key("totally bogus") is _KeyEnum.ctrl_r


def test_key_matches_handles_keycode_equality() -> None:
    a1 = _KeyCode("a")
    a2 = _KeyCode("a")
    b = _KeyCode("b")
    assert hotkey.key_matches(a1, a2)
    assert not hotkey.key_matches(a1, b)


def test_key_matches_handles_named_key_equality() -> None:
    assert hotkey.key_matches(_KeyEnum.ctrl_r, _KeyEnum.ctrl_r)
    assert not hotkey.key_matches(_KeyEnum.ctrl_r, _KeyEnum.ctrl_l)
