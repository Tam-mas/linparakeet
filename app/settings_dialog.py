from typing import Optional

from pynput import keyboard
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .config import Config
from .recorder import list_microphones

# Verified Hugging Face model IDs. The settings.json `model` field accepts any
# string, so power users can paste an unlisted model ID directly.
MODELS = [
    "nvidia/parakeet-tdt-0.6b-v2",
    "nvidia/parakeet-tdt-1.1b",
]


def key_to_spec(key) -> str:
    if isinstance(key, keyboard.KeyCode) and key.char:
        return key.char.lower()
    name = getattr(key, "name", None)
    if not name:
        return "right ctrl"
    return name.replace("_r", " r").replace("_l", " l").replace("_", " ").replace(" r", "_right").replace(" l", "_left")


def pretty_key_name(key) -> str:
    if isinstance(key, keyboard.KeyCode) and key.char:
        return key.char.upper()
    name = getattr(key, "name", str(key))
    mapping = {
        "ctrl_r": "Right Ctrl", "ctrl_l": "Left Ctrl",
        "alt_r": "Right Alt", "alt_l": "Left Alt",
        "shift_r": "Right Shift", "shift_l": "Left Shift",
        "caps_lock": "Caps Lock",
    }
    return mapping.get(name, name.replace("_", " ").title())


def spec_to_pretty(spec: str) -> str:
    mapping = {
        "right ctrl": "Right Ctrl", "left ctrl": "Left Ctrl",
        "right alt": "Right Alt", "left alt": "Left Alt",
        "right shift": "Right Shift", "left shift": "Left Shift",
        "caps lock": "Caps Lock", "space": "Space", "tab": "Tab",
    }
    if spec in mapping:
        return mapping[spec]
    if len(spec) == 1:
        return spec.upper()
    return spec.title()


class KeyCaptureDialog(QDialog):
    captured = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Press a key")
        self.setModal(True)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Press the key you want to use as the hotkey.\n(Press Esc to cancel.)"))
        self._listener: Optional[keyboard.Listener] = None

    def showEvent(self, event):
        super().showEvent(event)
        self._listener = keyboard.Listener(on_press=self._on_press)
        self._listener.start()

    def closeEvent(self, event):
        if self._listener:
            self._listener.stop()
            self._listener = None
        super().closeEvent(event)

    def _on_press(self, key):
        if key == keyboard.Key.esc:
            self.reject()
            return False
        spec = self._key_to_spec(key)
        self.captured.emit(spec)
        self.accept()
        return False

    @staticmethod
    def _key_to_spec(key) -> str:
        if isinstance(key, keyboard.KeyCode) and key.char:
            return key.char.lower()
        name = getattr(key, "name", "")
        direct = {
            "ctrl_r": "right ctrl", "ctrl_l": "left ctrl",
            "alt_r": "right alt", "alt_l": "left alt",
            "shift_r": "right shift", "shift_l": "left shift",
            "caps_lock": "caps lock",
        }
        if name in direct:
            return direct[name]
        return name.replace("_", " ")


class SettingsDialog(QDialog):
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("LinParakeet Settings")
        self.setMinimumWidth(480)

        tabs = QTabWidget()
        tabs.addTab(self._build_general(), "General")
        tabs.addTab(self._build_hotkey(), "Hotkey")
        tabs.addTab(self._build_audio(), "Audio")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)

    def _build_general(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.chk_chime = QCheckBox("Play chime when transcription completes")
        self.chk_chime.setChecked(self.config.play_chime)
        self.chk_paste = QCheckBox("Auto-paste into active window")
        self.chk_paste.setChecked(self.config.auto_paste)
        self.chk_autostart = QCheckBox("Launch at login")
        self.chk_autostart.setChecked(self.config.launch_at_startup)

        self.cmb_model = QComboBox()
        self.cmb_model.addItems(MODELS)
        if self.config.model in MODELS:
            self.cmb_model.setCurrentText(self.config.model)
        else:
            self.cmb_model.addItem(self.config.model)
            self.cmb_model.setCurrentText(self.config.model)

        form.addRow(self.chk_chime)
        form.addRow(self.chk_paste)
        form.addRow(self.chk_autostart)
        form.addRow("Model:", self.cmb_model)
        note = QLabel("Changing the model requires restarting LinParakeet.")
        note.setStyleSheet("color: #888; font-size: 11px;")
        form.addRow(note)
        return w

    def _build_hotkey(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        row = QWidget()
        row_l = QHBoxLayout(row)
        row_l.setContentsMargins(0, 0, 0, 0)
        self.lbl_hotkey = QLabel(spec_to_pretty(self.config.hotkey))
        self.lbl_hotkey.setStyleSheet("padding: 4px 10px; border: 1px solid #888; border-radius: 4px;")
        btn_rebind = QPushButton("Rebind...")
        btn_rebind.clicked.connect(self._rebind)
        row_l.addWidget(self.lbl_hotkey, 1)
        row_l.addWidget(btn_rebind)

        self.rb_toggle = QRadioButton("Hold for N seconds to toggle (start/stop)")
        self.rb_hold = QRadioButton("Hold to record (release to stop)")
        if self.config.hold_to_record:
            self.rb_hold.setChecked(True)
        else:
            self.rb_toggle.setChecked(True)

        self.spn_hold = QDoubleSpinBox()
        self.spn_hold.setRange(0.3, 10.0)
        self.spn_hold.setSingleStep(0.1)
        self.spn_hold.setSuffix(" s")
        self.spn_hold.setValue(self.config.hold_duration)

        form.addRow("Hotkey:", row)
        form.addRow(self.rb_toggle)
        form.addRow(self.rb_hold)
        form.addRow("Hold duration:", self.spn_hold)

        self._pending_hotkey = self.config.hotkey
        return w

    def _build_audio(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        self.cmb_mic = QComboBox()
        self.cmb_mic.addItem("Default (system)", None)
        try:
            for mic in list_microphones():
                label = mic.label
                if mic.is_bluetooth:
                    label = f"🎧 {label}"
                self.cmb_mic.addItem(label, mic.pa_source_name or mic.sd_device_index)
            if self.config.microphone is not None:
                for i in range(self.cmb_mic.count()):
                    if self.cmb_mic.itemData(i) == self.config.microphone:
                        self.cmb_mic.setCurrentIndex(i)
                        break
        except Exception as e:
            self.cmb_mic.addItem(f"(error listing devices: {e})")

        chime_row = QWidget()
        chime_l = QHBoxLayout(chime_row)
        chime_l.setContentsMargins(0, 0, 0, 0)
        self.edt_chime = QLineEdit(self.config.chime_file or "")
        self.edt_chime.setPlaceholderText("(default generated tone)")
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse_chime)
        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(lambda: self.edt_chime.setText(""))
        chime_l.addWidget(self.edt_chime, 1)
        chime_l.addWidget(btn_browse)
        chime_l.addWidget(btn_clear)

        form.addRow("Microphone:", self.cmb_mic)
        form.addRow("Chime sound:", chime_row)
        return w

    def _rebind(self):
        dlg = KeyCaptureDialog(self)
        dlg.captured.connect(self._on_captured)
        dlg.exec()

    def _on_captured(self, spec: str):
        self._pending_hotkey = spec
        self.lbl_hotkey.setText(spec_to_pretty(spec))

    def _browse_chime(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select chime sound", "", "Audio (*.wav *.mp3 *.ogg *.flac)"
        )
        if path:
            self.edt_chime.setText(path)

    def _accept(self):
        self.config.play_chime = self.chk_chime.isChecked()
        self.config.auto_paste = self.chk_paste.isChecked()
        self.config.launch_at_startup = self.chk_autostart.isChecked()
        self.config.model = self.cmb_model.currentText()
        self.config.hotkey = self._pending_hotkey
        self.config.hold_to_record = self.rb_hold.isChecked()
        self.config.hold_duration = self.spn_hold.value()
        self.config.microphone = self.cmb_mic.currentData()
        self.config.chime_file = self.edt_chime.text().strip() or None
        self.config.save()
        self.accept()
