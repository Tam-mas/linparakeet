import os
import shutil
import subprocess
from typing import Optional

import pyperclip


def display_server() -> str:
    return os.environ.get("XDG_SESSION_TYPE", "x11").lower()


def is_wayland() -> bool:
    return display_server() == "wayland"


def copy_to_clipboard(text: str) -> None:
    if is_wayland() and shutil.which("wl-copy"):
        subprocess.run(["wl-copy"], input=text.encode(), check=False)
        return
    try:
        pyperclip.copy(text)
    except pyperclip.PyperclipException:
        if shutil.which("xclip"):
            subprocess.run(
                ["xclip", "-selection", "clipboard"],
                input=text.encode(),
                check=False,
            )


def get_active_window_id() -> Optional[str]:
    if is_wayland():
        return None
    if not shutil.which("xdotool"):
        return None
    try:
        out = subprocess.run(
            ["xdotool", "getactivewindow"],
            capture_output=True, text=True, check=True, timeout=2,
        )
        return out.stdout.strip() or None
    except (subprocess.SubprocessError, OSError):
        return None


def auto_paste(window_id: Optional[str]) -> bool:
    if is_wayland():
        if shutil.which("ydotool"):
            try:
                subprocess.run(
                    ["ydotool", "key", "29:1", "47:1", "47:0", "29:0"],
                    check=False, timeout=2,
                )
                return True
            except (subprocess.SubprocessError, OSError):
                return False
        return False

    if not shutil.which("xdotool"):
        return False

    try:
        if window_id:
            subprocess.run(
                ["xdotool", "windowactivate", "--sync", window_id],
                check=False, timeout=2,
            )
        subprocess.run(
            ["xdotool", "key", "--clearmodifiers", "ctrl+v"],
            check=False, timeout=2,
        )
        return True
    except (subprocess.SubprocessError, OSError):
        return False
