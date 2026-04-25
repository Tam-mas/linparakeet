import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Optional, Union

CONFIG_DIR = Path(os.path.expanduser("~/.config/linparakeet"))
CONFIG_PATH = CONFIG_DIR / "settings.json"


@dataclass
class Config:
    hotkey: str = "right ctrl"
    hold_to_record: bool = False
    hold_duration: float = 1.0
    play_chime: bool = True
    auto_paste: bool = True
    microphone: Optional[Union[str, int]] = None  # PA source name or sounddevice index; None = system default
    model: str = "nvidia/parakeet-tdt-0.6b-v2"
    launch_at_startup: bool = True
    chime_file: Optional[str] = None
    first_run_complete: bool = False

    @classmethod
    def load(cls) -> "Config":
        if not CONFIG_PATH.exists():
            cfg = cls()
            cfg.save()
            return cfg
        try:
            with open(CONFIG_PATH) as f:
                data = json.load(f)
            known = {f.name for f in fields(cls)}
            return cls(**{k: v for k, v in data.items() if k in known})
        except (json.JSONDecodeError, TypeError, OSError):
            return cls()

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        # Atomic write: dump to a sibling temp file, then rename. A crash mid-write
        # leaves the previous good config intact instead of a truncated JSON that
        # load() would silently reset to defaults.
        tmp_path = CONFIG_PATH.with_suffix(".json.tmp")
        with open(tmp_path, "w") as f:
            json.dump(asdict(self), f, indent=2)
        os.replace(tmp_path, CONFIG_PATH)
