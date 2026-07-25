"""
Library view for Audook
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont
from typing import List

from app.models import Audiobook, Library, ServerConfig


class LibraryView(QWidget):
    """Library view for browsing audiobooks"""

    # Signals
    audiobook_selected = pyqtSignal(object, dict)
    audiobook_double_clicked = pyqtSignal(object)
    library_changed = pyqtSignal(str)
    server_changed = pyqtSignal(str)
    refresh_requested = pyqtSignal()
    search_requested = pyqtSignal(str)
    download_requested = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._libraries = []
        self._audiobooks = []
        self._current_server = None
        self._current_library = None
        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        label = QLabel("Bibliothèque")
        label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(label)

    def set_servers(self, servers: List[ServerConfig]):
        """Set available servers"""
        pass

    def set_current_server(self, server_id: str):
        """Set current server"""
        self._current_server = server_id

    def set_libraries(self, libraries: List[Library]):
        """Set available libraries"""
        self._libraries = libraries

    def set_current_library(self, library_id: str):
        """Set current library"""
        self._current_library = library_id

    def set_audiobooks(self, audiobooks: List[Audiobook]):
        """Set audiobooks to display"""
        self._audiobooks = audiobooks
