#!/usr/bin/env python3
import os
import signal
import sys
from typing import Optional

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication, QMessageBox

from app import autostart, chime, clipboard
from app.config import Config
from app.hotkey import HotkeyListener
from app.recorder import MicDevice, RecorderWorker, list_microphones
from app.settings_dialog import SettingsDialog
from app.transcriber import Transcriber, TranscriptionWorker, cleanup_stale_audio
from app.tray import State, TrayIcon


class AppController(QObject):
    trigger_start = Signal()
    trigger_stop = Signal()

    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.config = Config.load()

        # Wipe any audio temp files left over from a previous crashed session,
        # so the README's "audio is ephemeral" promise holds across crashes too.
        cleanup_stale_audio()

        self.transcriber = Transcriber(self.config.model)
        self.transcriber.ready.connect(self._on_model_ready)
        self.transcriber.load_failed.connect(self._on_model_failed)

        self.tray = TrayIcon(
            on_settings=self.open_settings,
            on_toggle_chime=self._toggle_chime,
            on_toggle_autopaste=self._toggle_autopaste,
            on_quit=self.quit,
            chime_enabled=self.config.play_chime,
            autopaste_enabled=self.config.auto_paste,
        )
        self.tray.show()

        self.recorder: Optional[RecorderWorker] = None
        self.transcription_worker: Optional[TranscriptionWorker] = None
        self._captured_window: Optional[str] = None
        self._recording = False

        self.trigger_start.connect(self._start_recording)
        self.trigger_stop.connect(self._stop_recording)

        self.hotkey = HotkeyListener(
            key_spec=self.config.hotkey,
            hold_duration=self.config.hold_duration,
            hold_to_record=self.config.hold_to_record,
            on_start=lambda: self.trigger_start.emit(),
            on_stop=lambda: self.trigger_stop.emit(),
        )
        self.hotkey.start()

        autostart.sync_autostart(self.config.launch_at_startup)

        if clipboard.is_wayland():
            self.tray.showMessage(
                "LinParakeet",
                "Wayland detected. Global hotkeys and auto-paste may be limited; install ydotool for paste support.",
                msecs=8000,
            )

        QTimer.singleShot(500, lambda: self.transcriber.load(show_dialog=True))

    def _resolve_mic(self) -> Optional[MicDevice]:
        pa_name = self.config.microphone
        if pa_name is None:
            return None
        try:
            for mic in list_microphones():
                if mic.pa_source_name == pa_name or str(mic.sd_device_index) == str(pa_name):
                    return mic
        except Exception:
            pass
        return None

    def _on_model_ready(self, device: str):
        if device == "cpu":
            self.tray.showMessage(
                "LinParakeet — running on CPU",
                "No GPU had enough free VRAM. Transcription will be slower; close other GPU apps and restart for best speed.",
                msecs=8000,
            )
        else:
            self.tray.showMessage("LinParakeet", f"Ready on {device}.", msecs=3000)

    def _on_model_failed(self, msg: str):
        QMessageBox.critical(
            None, "Model load failed",
            f"Could not load the Parakeet model:\n\n{msg}\n\nOpen Settings to change model."
        )

    def _start_recording(self):
        if self._recording:
            return
        if self.transcriber.model is None:
            self.tray.showMessage("LinParakeet", "Model still loading — try again shortly.", msecs=3000)
            self.hotkey.notify_stopped_externally()
            return

        self._captured_window = clipboard.get_active_window_id()
        self._recording = True
        self.tray.set_state(State.RECORDING)

        mic = self._resolve_mic()
        self.recorder = RecorderWorker(mic=mic)
        self.recorder.finished_audio.connect(self._on_audio_ready)
        self.recorder.error.connect(self._on_recorder_error)
        self.recorder.start()

    def _stop_recording(self):
        if not self._recording or not self.recorder:
            return
        self._recording = False
        self.tray.set_state(State.PROCESSING)
        self.recorder.stop()

    def _on_audio_ready(self, audio):
        if audio is None or len(audio) < 1600:
            self.tray.set_state(State.IDLE)
            self.tray.showMessage("LinParakeet", "Recording too short — ignored.", msecs=2500)
            return

        self.transcription_worker = TranscriptionWorker(self.transcriber, audio)
        self.transcription_worker.result.connect(self._on_transcription)
        self.transcription_worker.error.connect(self._on_transcription_error)
        self.transcription_worker.cpu_fallback.connect(self._on_cpu_fallback)
        self.transcription_worker.start()

    def _on_recorder_error(self, msg: str):
        self._recording = False
        self.tray.set_state(State.IDLE)
        self.hotkey.notify_stopped_externally()
        QMessageBox.warning(None, "Recording error", msg)

    def _on_transcription(self, text: str):
        self.tray.set_state(State.IDLE)
        text = (text or "").strip()
        if not text:
            self.tray.showMessage("LinParakeet", "No speech detected.", msecs=2500)
            return

        clipboard.copy_to_clipboard(text)
        if self.config.auto_paste:
            clipboard.auto_paste(self._captured_window)
        if self.config.play_chime:
            chime.play_chime(self.config.chime_file)

        preview = text if len(text) < 90 else text[:87] + "..."
        self.tray.showMessage("Transcribed", preview, msecs=3500)

    def _on_cpu_fallback(self, reason: str):
        short = reason.splitlines()[0] if reason else "GPU OOM"
        self.tray.showMessage(
            "GPU out of memory",
            f"Transcription fell back to CPU and will stay on CPU until restart.\n({short[:120]})",
            msecs=8000,
        )

    def _on_transcription_error(self, msg: str):
        self.tray.set_state(State.IDLE)
        QMessageBox.warning(None, "Transcription error", msg)

    def open_settings(self):
        old_model = self.config.model
        dlg = SettingsDialog(self.config)
        if dlg.exec():
            self.hotkey.update(
                key_spec=self.config.hotkey,
                hold_duration=self.config.hold_duration,
                hold_to_record=self.config.hold_to_record,
            )
            self.tray.refresh_toggles(self.config.play_chime, self.config.auto_paste)
            autostart.sync_autostart(self.config.launch_at_startup)
            if self.config.model != old_model:
                QMessageBox.information(
                    None, "Restart required",
                    "The selected model will be loaded the next time you start LinParakeet."
                )

    def _toggle_chime(self):
        self.config.play_chime = not self.config.play_chime
        self.config.save()
        self.tray.refresh_toggles(self.config.play_chime, self.config.auto_paste)

    def _toggle_autopaste(self):
        self.config.auto_paste = not self.config.auto_paste
        self.config.save()
        self.tray.refresh_toggles(self.config.play_chime, self.config.auto_paste)

    def quit(self):
        self.hotkey.stop()
        self.app.quit()


def main():
    os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("LinParakeet")

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    controller = AppController(app)
    _ = controller
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
