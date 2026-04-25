import time
from typing import Callable, Optional

from pynput import keyboard


def parse_key(spec: str):
    s = spec.strip().lower()
    aliases = {
        "right ctrl": keyboard.Key.ctrl_r,
        "left ctrl": keyboard.Key.ctrl_l,
        "ctrl": keyboard.Key.ctrl,
        "right alt": keyboard.Key.alt_r,
        "left alt": keyboard.Key.alt_l,
        "alt": keyboard.Key.alt,
        "right shift": keyboard.Key.shift_r,
        "left shift": keyboard.Key.shift_l,
        "shift": keyboard.Key.shift,
        "space": keyboard.Key.space,
        "tab": keyboard.Key.tab,
        "caps lock": keyboard.Key.caps_lock,
        "f1": keyboard.Key.f1, "f2": keyboard.Key.f2, "f3": keyboard.Key.f3,
        "f4": keyboard.Key.f4, "f5": keyboard.Key.f5, "f6": keyboard.Key.f6,
        "f7": keyboard.Key.f7, "f8": keyboard.Key.f8, "f9": keyboard.Key.f9,
        "f10": keyboard.Key.f10, "f11": keyboard.Key.f11, "f12": keyboard.Key.f12,
    }
    if s in aliases:
        return aliases[s]
    if len(s) == 1:
        return keyboard.KeyCode.from_char(s)
    return keyboard.Key.ctrl_r


def key_matches(pressed, target) -> bool:
    if pressed == target:
        return True
    if isinstance(pressed, keyboard.KeyCode) and isinstance(target, keyboard.KeyCode):
        return pressed.char == target.char
    return False


class HotkeyListener:
    def __init__(
        self,
        key_spec: str,
        hold_duration: float,
        hold_to_record: bool,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
    ):
        self.target_key = parse_key(key_spec)
        self.hold_duration = hold_duration
        self.hold_to_record = hold_to_record
        self.on_start = on_start
        self.on_stop = on_stop

        self._recording = False
        self._key_down_at: Optional[float] = None
        self._listener: Optional[keyboard.Listener] = None

    def start(self):
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()
            self._listener = None

    def update(self, key_spec: str, hold_duration: float, hold_to_record: bool):
        self.target_key = parse_key(key_spec)
        self.hold_duration = hold_duration
        self.hold_to_record = hold_to_record
        self._key_down_at = None

    def notify_stopped_externally(self):
        self._recording = False

    def _on_press(self, key):
        if not key_matches(key, self.target_key):
            return
        if self.hold_to_record:
            if not self._recording:
                self._recording = True
                self.on_start()
        else:
            if self._key_down_at is None:
                self._key_down_at = time.monotonic()

    def _on_release(self, key):
        if not key_matches(key, self.target_key):
            return
        if self.hold_to_record:
            if self._recording:
                self._recording = False
                self.on_stop()
        else:
            if self._key_down_at is None:
                return
            held = time.monotonic() - self._key_down_at
            self._key_down_at = None
            if held >= self.hold_duration:
                if self._recording:
                    self._recording = False
                    self.on_stop()
                else:
                    self._recording = True
                    self.on_start()
