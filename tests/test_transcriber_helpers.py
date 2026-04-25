"""Pure-logic helpers in transcriber: VRAM thresholds, OOM detection, audio cleanup."""
import sys
import types
from pathlib import Path

import pytest


# Stub PySide6 + numpy + scipy + nemo just enough that `import app.transcriber`
# succeeds in CI environments without those heavy deps installed.
def _stub_module(name: str, attrs: dict | None = None) -> types.ModuleType:
    m = types.ModuleType(name)
    for k, v in (attrs or {}).items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m


_stub_module("PySide6")
_stub_module("PySide6.QtCore", {
    "QObject": type("QObject", (), {"__init__": lambda self, *a, **k: None}),
    "QThread": type("QThread", (), {"__init__": lambda self, *a, **k: None}),
    "Signal": lambda *a, **k: None,
})
_stub_module("PySide6.QtWidgets", {
    "QDialog": type("QDialog", (), {"__init__": lambda self, *a, **k: None}),
    "QLabel": type("QLabel", (), {"__init__": lambda self, *a, **k: None}),
    "QProgressBar": type("QProgressBar", (), {"__init__": lambda self, *a, **k: None}),
    "QVBoxLayout": type("QVBoxLayout", (), {"__init__": lambda self, *a, **k: None}),
})
_stub_module("numpy", {"ndarray": object})

from app import transcriber  # noqa: E402


def test_required_vram_06b_family() -> None:
    assert transcriber._required_vram_gb("nvidia/parakeet-tdt-0.6b-v2") == 3.0
    assert transcriber._required_vram_gb("nvidia/parakeet-tdt-0.6b-v3") == 3.0


def test_required_vram_11b_uses_higher_threshold() -> None:
    assert transcriber._required_vram_gb("nvidia/parakeet-tdt-1.1b") == 5.0


def test_oom_detection_strings() -> None:
    assert transcriber._is_oom_error(RuntimeError("CUDA out of memory. Tried to allocate ..."))
    assert transcriber._is_oom_error(RuntimeError("cudaErrorMemoryAllocation"))
    assert transcriber._is_oom_error(RuntimeError("CUDA error: alloc failed"))
    assert transcriber._is_oom_error(MemoryError("host OOM"))
    assert not transcriber._is_oom_error(ValueError("audio file truncated"))


def test_cleanup_stale_audio_wipes_only_wavs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "leftover.wav").write_bytes(b"RIFF")
    (cache / "another.wav").write_bytes(b"RIFF")
    keep = cache / "notes.txt"
    keep.write_text("not audio")

    monkeypatch.setattr(transcriber, "AUDIO_CACHE_DIR", cache)
    transcriber.cleanup_stale_audio()

    assert not (cache / "leftover.wav").exists()
    assert not (cache / "another.wav").exists()
    assert keep.exists(), "non-wav files must be left alone"


def test_cleanup_stale_audio_handles_missing_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(transcriber, "AUDIO_CACHE_DIR", tmp_path / "does-not-exist")
    transcriber.cleanup_stale_audio()  # must not raise
