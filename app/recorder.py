import time
from dataclasses import dataclass
from typing import Optional

import numpy as np
import sounddevice as sd
from PySide6.QtCore import QThread, Signal

from .pulse import (
    get_default_source,
    list_bt_cards,
    list_pa_sources,
    set_default_source,
    switch_bt_profile,
    switch_bt_to_hsp,
)

SAMPLE_RATE = 16000
CHANNELS = 1


@dataclass
class MicDevice:
    """A selectable input device shown in Settings."""
    pa_source_name: Optional[str]   # PulseAudio source name (preferred)
    sd_device_index: Optional[int]  # sounddevice index (fallback)
    label: str
    is_bluetooth: bool = False
    bt_card_name: Optional[str] = None
    bt_a2dp_profile: Optional[str] = None  # profile to restore after recording


def list_microphones() -> list[MicDevice]:
    """Return deduplicated list of input devices, BT headsets included."""
    devices: list[MicDevice] = []

    pa_sources = list_pa_sources()
    bt_cards = {c.name: c for c in list_bt_cards()}

    for src in pa_sources:
        is_bt = src.is_bluetooth
        card_name = None
        a2dp_profile = None
        if is_bt:
            mac = src.name.split(".")[-1] if "." in src.name else ""
            for cname, card in bt_cards.items():
                if mac and mac in cname:
                    card_name = cname
                    a2dp_profile = card.active_profile
                    break
        devices.append(MicDevice(
            pa_source_name=src.name,
            sd_device_index=None,
            label=src.description,
            is_bluetooth=is_bt,
            bt_card_name=card_name,
            bt_a2dp_profile=a2dp_profile,
        ))

    if not devices:
        sd_devs = sd.query_devices()
        for idx, dev in enumerate(sd_devs):
            if dev["max_input_channels"] > 0 and dev["name"] not in ("pulse", "pipewire", "default"):
                devices.append(MicDevice(
                    pa_source_name=None,
                    sd_device_index=idx,
                    label=f"{dev['name']} (ALSA)",
                    is_bluetooth=False,
                ))

    return devices


class RecorderWorker(QThread):
    finished_audio = Signal(object)
    error = Signal(str)

    def __init__(self, mic: Optional[MicDevice] = None):
        super().__init__()
        self.mic = mic
        self._chunks: list[np.ndarray] = []
        self._stop = False
        self._prev_default_source: Optional[str] = None
        self._activated_hsp = False

    def run(self):
        self._chunks = []
        self._stop = False
        self._activated_hsp = False
        self._prev_default_source = None

        try:
            sd_device = self._prepare_device()
        except Exception as e:
            self.error.emit(f"Device setup failed: {e}")
            return

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                device=sd_device,
                dtype="float32",
                callback=self._callback,
            ):
                while not self._stop:
                    self.msleep(50)
        except Exception as e:
            self._restore_device()
            self.error.emit(f"Recording failed: {e}")
            return

        self._restore_device()

        if self._chunks:
            audio = np.concatenate(self._chunks, axis=0).flatten()
        else:
            audio = np.zeros(0, dtype=np.float32)
        self.finished_audio.emit(audio)

    def _prepare_device(self) -> Optional[int]:
        """Set up PA source / BT profile. Returns sounddevice device index to use."""
        mic = self.mic
        if mic is None:
            return None  # sounddevice default

        if mic.is_bluetooth and mic.bt_card_name:
            bt_cards = {c.name: c for c in list_bt_cards()}
            card = bt_cards.get(mic.bt_card_name)
            if card and not card.active_profile.startswith("headset"):
                activated = switch_bt_to_hsp(mic.bt_card_name)
                if activated:
                    self._activated_hsp = True
                    # Give PipeWire a moment to expose the new source
                    time.sleep(0.8)

        if mic.pa_source_name:
            self._prev_default_source = get_default_source()
            set_default_source(mic.pa_source_name)
            time.sleep(0.3)
            # Use pulse/pipewire virtual device so PA routes to our source
            sd_devs = sd.query_devices()
            for idx, dev in enumerate(sd_devs):
                if dev["name"] in ("pulse", "pipewire") and dev["max_input_channels"] > 0:
                    return idx
            return None

        return mic.sd_device_index

    def _restore_device(self):
        if self._prev_default_source:
            try:
                set_default_source(self._prev_default_source)
            except Exception:
                pass
            self._prev_default_source = None

        mic = self.mic
        if self._activated_hsp and mic and mic.bt_card_name and mic.bt_a2dp_profile:
            try:
                switch_bt_profile(mic.bt_card_name, mic.bt_a2dp_profile)
            except Exception:
                pass
            self._activated_hsp = False

    def _callback(self, indata, frames, time_info, status):
        self._chunks.append(indata.copy())

    def stop(self):
        self._stop = True
