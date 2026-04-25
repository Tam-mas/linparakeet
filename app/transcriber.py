import os
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout

# Audio is written briefly to disk for NeMo to read, then unlinked. We use a
# user-only cache dir (mode 0700) instead of /tmp so leftover WAVs from a crash
# stay inside the user's home, and so we can sweep stale files at startup.
AUDIO_CACHE_DIR = Path(os.path.expanduser("~/.cache/linparakeet/audio"))


def _ensure_cache_dir() -> Path:
    AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(AUDIO_CACHE_DIR, 0o700)
    except OSError:
        pass
    return AUDIO_CACHE_DIR


def cleanup_stale_audio() -> None:
    """Wipe any leftover WAVs from a previous crashed/killed session."""
    if not AUDIO_CACHE_DIR.exists():
        return
    for p in AUDIO_CACHE_DIR.glob("*.wav"):
        try:
            p.unlink()
        except OSError:
            pass


def _required_vram_gb(model_name: str) -> float:
    """Rough VRAM ceiling for model + activation overhead."""
    name = model_name.lower()
    if "1.1b" in name:
        return 5.0
    return 3.0  # 0.6b family


def pick_device(model_name: str) -> tuple[str, str]:
    """Choose the best device. Returns (device_str, reason)."""
    try:
        import torch
    except ImportError:
        return "cpu", "PyTorch not available"

    if not torch.cuda.is_available():
        return "cpu", "No CUDA available"

    required = _required_vram_gb(model_name) * (1024 ** 3)
    best_idx: Optional[int] = None
    best_free = 0
    per_gpu: list[tuple[int, float, float]] = []

    for i in range(torch.cuda.device_count()):
        try:
            free, total = torch.cuda.mem_get_info(i)
        except Exception:
            continue
        per_gpu.append((i, free / 1024 ** 3, total / 1024 ** 3))
        if free >= required and free > best_free:
            best_free = free
            best_idx = i

    if best_idx is not None:
        name = torch.cuda.get_device_name(best_idx)
        return f"cuda:{best_idx}", f"GPU {best_idx} ({name}, {best_free/1024**3:.1f} GB free)"

    summary = ", ".join(f"GPU{i}={free:.1f}/{total:.1f}GB" for i, free, total in per_gpu)
    return "cpu", f"No GPU with {_required_vram_gb(model_name):.0f} GB free ({summary}) — falling back to CPU"


class ModelLoader(QThread):
    loaded = Signal(object, str)  # model, device string
    status = Signal(str)
    error = Signal(str)

    def __init__(self, model_name: str):
        super().__init__()
        self.model_name = model_name

    def run(self):
        try:
            self.status.emit("Importing NeMo toolkit...")
            import nemo.collections.asr as nemo_asr

            device, reason = pick_device(self.model_name)
            self.status.emit(f"Loading {self.model_name} on {device}\n({reason})")

            model = nemo_asr.models.ASRModel.from_pretrained(
                model_name=self.model_name
            )

            try:
                model = model.to(device)
            except Exception as move_err:
                if device.startswith("cuda"):
                    self.status.emit(f"GPU move failed ({move_err}); falling back to CPU")
                    device = "cpu"
                    reason = f"GPU move failed: {move_err}"
                    model = model.to("cpu")
                else:
                    raise

            model.eval()
            self.loaded.emit(model, device)
        except Exception as e:
            self.error.emit(str(e))


class FirstRunDialog(QDialog):
    def __init__(self, model_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LinParakeet — First Run")
        self.setMinimumWidth(420)
        self.setModal(False)

        layout = QVBoxLayout(self)
        self.label = QLabel(f"Preparing {model_name}\nThis only runs once.")
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        layout.addWidget(self.progress)

    def set_status(self, text: str):
        self.label.setText(text)


def _is_oom_error(err: BaseException) -> bool:
    msg = str(err).lower()
    if "out of memory" in msg or "cudaerrormemoryallocation" in msg:
        return True
    if "cuda" in msg and "alloc" in msg:
        return True
    try:
        import torch
        if hasattr(torch.cuda, "OutOfMemoryError") and isinstance(err, torch.cuda.OutOfMemoryError):
            return True
    except ImportError:
        pass
    return isinstance(err, MemoryError)


class TranscriptionWorker(QThread):
    result = Signal(str)
    error = Signal(str)
    cpu_fallback = Signal(str)  # emitted when a GPU OOM forced a CPU retry

    def __init__(self, transcriber: "Transcriber", audio: np.ndarray):
        super().__init__()
        self.transcriber = transcriber
        self.audio = audio

    def run(self):
        try:
            if self.audio.size < 1600:
                self.result.emit("")
                return

            import scipy.io.wavfile as wavfile

            cache_dir = _ensure_cache_dir()
            with tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False, dir=str(cache_dir)
            ) as tmp:
                audio_int16 = np.clip(self.audio * 32767, -32768, 32767).astype(np.int16)
                wavfile.write(tmp.name, 16000, audio_int16)
                tmp_path = tmp.name

            try:
                try:
                    text = self._transcribe(tmp_path)
                except Exception as e:
                    if _is_oom_error(e) and self.transcriber.device != "cpu":
                        self._move_to_cpu()
                        self.cpu_fallback.emit(str(e))
                        text = self._transcribe(tmp_path)
                    else:
                        raise
                self.result.emit(text)
            finally:
                try:
                    Path(tmp_path).unlink()
                except OSError:
                    pass
        except Exception as e:
            self.error.emit(str(e))

    def _transcribe(self, path: str) -> str:
        output = self.transcriber.model.transcribe([path])
        return self._extract_text(output)

    def _move_to_cpu(self) -> None:
        """Move the shared model to CPU. Safe under our single-active-transcription invariant."""
        try:
            self.transcriber.model.to("cpu")
        except Exception:
            pass
        self.transcriber.device = "cpu"
        try:
            import torch
            torch.cuda.empty_cache()
        except Exception:
            pass

    @staticmethod
    def _extract_text(output) -> str:
        if not output:
            return ""
        first = output[0]
        if hasattr(first, "text"):
            return first.text
        if isinstance(first, str):
            return first
        if isinstance(first, (list, tuple)) and first:
            return str(first[0])
        return str(first)


class Transcriber(QObject):
    ready = Signal(str)  # device string ("cuda:0", "cpu", ...)
    load_failed = Signal(str)

    def __init__(self, model_name: str):
        super().__init__()
        self.model_name = model_name
        self.model = None
        self.device: str = "cpu"
        self._loader: Optional[ModelLoader] = None
        self._dialog: Optional[FirstRunDialog] = None

    def load(self, show_dialog: bool = True):
        if self.model is not None:
            self.ready.emit(self.device)
            return

        if show_dialog:
            self._dialog = FirstRunDialog(self.model_name)
            self._dialog.show()

        self._loader = ModelLoader(self.model_name)
        self._loader.status.connect(self._on_status)
        self._loader.loaded.connect(self._on_loaded)
        self._loader.error.connect(self._on_error)
        self._loader.start()

    def _on_status(self, msg: str):
        if self._dialog:
            self._dialog.set_status(msg)

    def _on_loaded(self, model, device: str):
        self.model = model
        self.device = device
        if self._dialog:
            self._dialog.accept()
            self._dialog = None
        self.ready.emit(device)

    def _on_error(self, msg: str):
        if self._dialog:
            self._dialog.reject()
            self._dialog = None
        self.load_failed.emit(msg)
