import os
import shlex
import sys
from pathlib import Path

AUTOSTART_DIR = Path(os.path.expanduser("~/.config/autostart"))
DESKTOP_PATH = AUTOSTART_DIR / "linparakeet.desktop"
TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "linparakeet.desktop"


def _launch_command() -> str:
    script = Path(__file__).resolve().parent.parent / "main.py"
    return f"{shlex.quote(sys.executable)} {shlex.quote(str(script))}"


def _render_desktop_entry(exec_cmd: str) -> str:
    template = TEMPLATE_PATH.read_text()
    return template.replace("__EXEC__", exec_cmd)


def enable_autostart() -> None:
    AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
    DESKTOP_PATH.write_text(_render_desktop_entry(_launch_command()))


def disable_autostart() -> None:
    if DESKTOP_PATH.exists():
        DESKTOP_PATH.unlink()


def sync_autostart(enabled: bool) -> None:
    if enabled:
        enable_autostart()
    else:
        disable_autostart()
