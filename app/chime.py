from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd


def _generate_chime(sample_rate: int = 44100) -> np.ndarray:
    dur_a, dur_b = 0.12, 0.18
    f_a, f_b = 660.0, 990.0
    t_a = np.linspace(0, dur_a, int(sample_rate * dur_a), endpoint=False)
    t_b = np.linspace(0, dur_b, int(sample_rate * dur_b), endpoint=False)
    tone_a = np.sin(2 * np.pi * f_a * t_a)
    tone_b = np.sin(2 * np.pi * f_b * t_b)
    env_a = np.exp(-3 * t_a / dur_a)
    env_b = np.exp(-3 * t_b / dur_b)
    signal = np.concatenate([tone_a * env_a, tone_b * env_b]).astype(np.float32)
    return signal * 0.3


_CACHED: Optional[np.ndarray] = None


def play_chime(chime_file: Optional[str] = None) -> None:
    global _CACHED
    try:
        if chime_file and Path(chime_file).exists():
            import scipy.io.wavfile as wavfile
            sr, data = wavfile.read(chime_file)
            if data.dtype != np.float32:
                data = data.astype(np.float32) / np.iinfo(data.dtype).max
            sd.play(data, sr)
            return

        if _CACHED is None:
            _CACHED = _generate_chime()
        sd.play(_CACHED, 44100)
    except Exception:
        pass
