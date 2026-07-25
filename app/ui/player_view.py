"""
Player view for Audook
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from typing import Optional

from app.models import Audiobook


class PlayerView(QWidget):
    """Player view for playback control"""

    # Signals
    play_pause_clicked = pyqtSignal()
    previous_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    seek_backward_clicked = pyqtSignal(int)
    seek_forward_clicked = pyqtSignal(int)
    volume_changed = pyqtSignal(float)
    speed_changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._audiobook: Optional[Audiobook] = None
        self._chapter: Optional[dict] = None
        self._init_ui()
        self._update_timer = QTimer(self)
        self._update_timer.start(100)

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        label = QLabel("Lecteur")
        label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(label)

    def set_audiobook(self, audiobook: Audiobook, chapter: dict):
        """Set the audiobook to display"""
        self._audiobook = audiobook
        self._chapter = chapter

    def get_current_audiobook(self) -> Optional[Audiobook]:
        """Get current audiobook"""
        return self._audiobook

    def get_current_chapter(self) -> Optional[dict]:
        """Get current chapter"""
        return self._chapter
