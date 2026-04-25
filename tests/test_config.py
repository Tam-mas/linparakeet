"""Config loads/saves cleanly and tolerates corrupt or unknown-key JSON."""
import json
from pathlib import Path

import pytest

from app import config as config_mod
from app.config import Config


@pytest.fixture(autouse=True)
def _redirect_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point CONFIG_DIR/CONFIG_PATH at a tmp dir for every test in this file."""
    cfg_dir = tmp_path / "linparakeet"
    monkeypatch.setattr(config_mod, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(config_mod, "CONFIG_PATH", cfg_dir / "settings.json")
    return cfg_dir


def test_load_creates_default_when_missing() -> None:
    cfg = Config.load()
    assert cfg.hotkey == "right ctrl"
    assert cfg.play_chime is True
    assert config_mod.CONFIG_PATH.exists(), "first load should write a default file"


def test_save_round_trip() -> None:
    cfg = Config.load()
    cfg.hotkey = "f9"
    cfg.hold_duration = 0.5
    cfg.microphone = "alsa_input.usb-foo"
    cfg.save()

    reloaded = Config.load()
    assert reloaded.hotkey == "f9"
    assert reloaded.hold_duration == 0.5
    assert reloaded.microphone == "alsa_input.usb-foo"


def test_save_is_atomic_no_tmp_left_behind() -> None:
    Config().save()
    assert not config_mod.CONFIG_PATH.with_suffix(".json.tmp").exists()


def test_load_tolerates_unknown_keys() -> None:
    config_mod.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config_mod.CONFIG_PATH.write_text(json.dumps({
        "hotkey": "f10",
        "future_setting_we_havent_invented_yet": 42,
    }))
    cfg = Config.load()
    assert cfg.hotkey == "f10"


def test_load_tolerates_corrupt_json() -> None:
    config_mod.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config_mod.CONFIG_PATH.write_text("{ this is not valid json")
    cfg = Config.load()
    # Should silently fall back to defaults rather than blow up the app.
    assert cfg.hotkey == "right ctrl"


def test_microphone_accepts_int_index() -> None:
    """sounddevice fallback stores an int index; serialisation must round-trip."""
    cfg = Config()
    cfg.microphone = 3
    cfg.save()
    reloaded = Config.load()
    assert reloaded.microphone == 3
