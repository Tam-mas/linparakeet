from enum import Enum
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


class State(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"


def _make_icon(color: QColor, ring: Optional[QColor] = None) -> QIcon:
    size = 64
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    if ring is not None:
        p.setPen(ring)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(4, 4, size - 8, size - 8)

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    p.drawRoundedRect(24, 14, 16, 26, 8, 8)
    p.drawRect(30, 40, 4, 10)
    p.drawRect(22, 48, 20, 3)
    p.setPen(color)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawArc(18, 22, 28, 24, 180 * 16, 180 * 16)
    p.end()
    return QIcon(pix)


class TrayIcon(QSystemTrayIcon):
    def __init__(
        self,
        on_settings: Callable[[], None],
        on_toggle_chime: Callable[[], None],
        on_toggle_autopaste: Callable[[], None],
        on_quit: Callable[[], None],
        chime_enabled: bool,
        autopaste_enabled: bool,
    ):
        super().__init__()
        self._icons = {
            State.IDLE: _make_icon(QColor("#8a8a8a")),
            State.RECORDING: _make_icon(QColor("#e53935"), QColor("#e53935")),
            State.PROCESSING: _make_icon(QColor("#fdd835")),
        }
        self.set_state(State.IDLE)

        menu = QMenu()
        act_settings = QAction("Settings...", menu)
        act_settings.triggered.connect(on_settings)
        menu.addAction(act_settings)
        menu.addSeparator()

        self.act_chime = QAction("Play chime on completion", menu, checkable=True)
        self.act_chime.setChecked(chime_enabled)
        self.act_chime.triggered.connect(on_toggle_chime)
        menu.addAction(self.act_chime)

        self.act_paste = QAction("Auto-paste", menu, checkable=True)
        self.act_paste.setChecked(autopaste_enabled)
        self.act_paste.triggered.connect(on_toggle_autopaste)
        menu.addAction(self.act_paste)

        menu.addSeparator()
        act_quit = QAction("Quit", menu)
        act_quit.triggered.connect(on_quit)
        menu.addAction(act_quit)

        self.setContextMenu(menu)
        self.setToolTip("LinParakeet — idle")

    def set_state(self, state: State):
        self.setIcon(self._icons[state])
        labels = {
            State.IDLE: "LinParakeet — idle",
            State.RECORDING: "LinParakeet — recording...",
            State.PROCESSING: "LinParakeet — transcribing...",
        }
        self.setToolTip(labels[state])

    def refresh_toggles(self, chime: bool, autopaste: bool):
        self.act_chime.setChecked(chime)
        self.act_paste.setChecked(autopaste)
