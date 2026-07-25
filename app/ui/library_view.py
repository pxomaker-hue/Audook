"""
Library view - Display audiobooks in a modern grid layout
"""

from typing import List, Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea,
    QPushButton, QLineEdit, QLabel, QFrame, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QIcon, QFont
from pathlib import Path

from app.models import Audiobook, Library, ServerConfig
from app.utils.cover_generator import get_or_create_cover
from app.utils import logger


class AudiobookCard(QFrame):
    """Card widget for displaying an audiobook"""

    clicked = pyqtSignal(Audiobook)
    double_clicked = pyqtSignal(Audiobook)

    def __init__(self, audiobook: Audiobook):
        super().__init__()
        self.audiobook = audiobook
        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            AudiobookCard {
                background-color: #1a2332;
                border-radius: 8px;
                padding: 8px;
                border: 1px solid #2a3f5f;
            }
            AudiobookCard:hover {
                border: 2px solid #4a6fa5;
                background-color: #222a3a;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Cover image
        cover_label = QLabel()
        cover_label.setFixedSize(180, 240)
        cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        try:
            covers_dir = Path("app/assets/covers")
            covers_dir.mkdir(parents=True, exist_ok=True)

            cover_path = get_or_create_cover(
                self.audiobook.id,
                self.audiobook.title,
                self.audiobook.author,
                covers_dir
            )

            pixmap = QPixmap(str(cover_path))
            if not pixmap.isNull():
                pixmap = pixmap.scaledToWidth(180, Qt.TransformationMode.SmoothTransformation)
                cover_label.setPixmap(pixmap)
            else:
                cover_label.setText("No Cover")
                cover_label.setStyleSheet("background-color: #2a3f5f; color: #888;")
        except Exception as e:
            logger.error(f"Failed to load cover: {e}")
            cover_label.setText("No Cover")
            cover_label.setStyleSheet("background-color: #2a3f5f; color: #888;")

        layout.addWidget(cover_label)

        # Title
        title_label = QLabel(self.audiobook.title)
        title_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title_label.setWordWrap(True)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #fff; padding: 4px;")
        layout.addWidget(title_label)

        # Author
        author_label = QLabel(self.audiobook.author)
        author_label.setFont(QFont("Segoe UI", 9))
        author_label.setWordWrap(True)
        author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        author_label.setStyleSheet("color: #aaa; padding: 0px 4px;")
        layout.addWidget(author_label)

        # Chapters count
        chapters_count = len(self.audiobook.chapters) if self.audiobook.chapters else 0
        chapters_label = QLabel(f"{chapters_count} chapitres")
        chapters_label.setFont(QFont("Segoe UI", 8))
        chapters_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chapters_label.setStyleSheet("color: #888; padding: 2px 4px;")
        layout.addWidget(chapters_label)

        layout.addStretch()

    def mouseDoubleClickEvent(self, event):
        """Handle double click"""
        self.double_clicked.emit(self.audiobook)

    def mousePressEvent(self, event):
        """Handle single click"""
        self.clicked.emit(self.audiobook)


class LibraryView(QWidget):
    """Library view widget"""

    audiobook_selected = pyqtSignal(Audiobook, dict)
    audiobook_double_clicked = pyqtSignal(Audiobook)
    library_changed = pyqtSignal(str)
    server_changed = pyqtSignal(str)
    refresh_requested = pyqtSignal()
    search_requested = pyqtSignal(str)
    download_requested = pyqtSignal(Audiobook)

    def __init__(self):
        super().__init__()
        self._servers: List[ServerConfig] = []
        self._libraries: List[Library] = []
        self._audiobooks: List[Audiobook] = []
        self._current_server: Optional[ServerConfig] = None
        self._current_library: Optional[Library] = None
        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = self._create_header()
        layout.addWidget(header)

        # Content area
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)

        # Search bar
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)

        search_input = QLineEdit()
        search_input.setPlaceholderText("Rechercher...")
        search_input.setMaximumHeight(40)
        search_input.setStyleSheet("""
            QLineEdit {
                background-color: #2a3f5f;
                border: 1px solid #3a5f7f;
                border-radius: 6px;
                color: #fff;
                padding: 8px 12px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #4a7fa5;
            }
        """)
        search_input.textChanged.connect(self._on_search_text_changed)
        self._search_input = search_input

        search_layout.addWidget(search_input)

        refresh_btn = QPushButton("↻ Actualiser")
        refresh_btn.setMaximumHeight(40)
        refresh_btn.setMaximumWidth(150)
        refresh_btn.clicked.connect(self.refresh_requested.emit)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a5f7f;
                border: 1px solid #4a7fa5;
                border-radius: 6px;
                color: #fff;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4a7fa5;
            }
        """)

        search_layout.addWidget(refresh_btn)
        content_layout.addLayout(search_layout)

        # Scroll area for audiobooks grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #0d1117; }")

        grid_widget = QWidget()
        self._grid_layout = QGridLayout(grid_widget)
        self._grid_layout.setSpacing(16)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area.setWidget(grid_widget)
        content_layout.addWidget(scroll_area)

        # Add content to main layout
        content_widget = QWidget()
        content_widget.setLayout(content_layout)
        layout.addWidget(content_widget)

    def _create_header(self) -> QWidget:
        """Create header with server and library selection"""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #0d1117;
                border-bottom: 1px solid #3a5f7f;
            }
        """)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)

        # Server selector
        server_label = QLabel("Serveur:")
        server_label.setStyleSheet("color: #aaa; font-weight: bold;")

        self._server_combo = QComboBox()
        self._server_combo.setMinimumWidth(200)
        self._server_combo.currentTextChanged.connect(self._on_server_changed)
        self._server_combo.setStyleSheet("""
            QComboBox {
                background-color: #2a3f5f;
                border: 1px solid #3a5f7f;
                border-radius: 4px;
                color: #fff;
                padding: 6px;
            }
        """)

        layout.addWidget(server_label)
        layout.addWidget(self._server_combo)

        # Library selector
        library_label = QLabel("Bibliothèque:")
        library_label.setStyleSheet("color: #aaa; font-weight: bold;")

        self._library_combo = QComboBox()
        self._library_combo.setMinimumWidth(200)
        self._library_combo.currentTextChanged.connect(self._on_library_changed)
        self._library_combo.setStyleSheet("""
            QComboBox {
                background-color: #2a3f5f;
                border: 1px solid #3a5f7f;
                border-radius: 4px;
                color: #fff;
                padding: 6px;
            }
        """)

        layout.addWidget(library_label)
        layout.addWidget(self._library_combo)

        # Title
        title = QLabel("Bibliothèque")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #fff; margin-left: 20px;")

        layout.addStretch()
        layout.addWidget(title, 0, Qt.AlignmentFlag.AlignRight)

        return header

    def set_servers(self, servers: List[ServerConfig]):
        """Set available servers"""
        self._servers = servers
        self._server_combo.blockSignals(True)
        self._server_combo.clear()

        self._server_combo.addItem("Local", "local")
        for server in servers:
            self._server_combo.addItem(server.name, server.id)

        self._server_combo.blockSignals(False)

    def set_libraries(self, libraries: List[Library]):
        """Set available libraries"""
        self._libraries = libraries
        self._library_combo.blockSignals(True)
        self._library_combo.clear()

        for lib in libraries:
            self._library_combo.addItem(lib.name, lib.id)

        self._library_combo.blockSignals(False)

    def set_audiobooks(self, audiobooks: List[Audiobook]):
        """Display audiobooks in grid"""
        self._audiobooks = audiobooks

        # Clear grid
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add audiobook cards
        columns = 4
        for idx, audiobook in enumerate(audiobooks):
            card = AudiobookCard(audiobook)
            card.clicked.connect(lambda ab, ch=None: self._on_audiobook_selected(ab, ch))
            card.double_clicked.connect(self.audiobook_double_clicked.emit)

            row = idx // columns
            col = idx % columns
            self._grid_layout.addWidget(card, row, col)

        # Add stretch at the end
        self._grid_layout.addItem(
            self._grid_layout.itemAt(self._grid_layout.count() - 1) or
            self._grid_layout.addStretch(self._grid_layout.rowCount(), 0)
        )

    def set_current_server(self, server_id: str):
        """Set current server"""
        index = self._server_combo.findData(server_id)
        if index >= 0:
            self._server_combo.setCurrentIndex(index)

    def set_current_library(self, library_id: str):
        """Set current library"""
        index = self._library_combo.findData(library_id)
        if index >= 0:
            self._library_combo.setCurrentIndex(index)

    def _on_server_changed(self, text: str):
        """Handle server selection change"""
        server_id = self._server_combo.currentData()
        if server_id:
            self.server_changed.emit(server_id)

    def _on_library_changed(self, text: str):
        """Handle library selection change"""
        library_id = self._library_combo.currentData()
        if library_id:
            self.library_changed.emit(library_id)

    def _on_audiobook_selected(self, audiobook: Audiobook, chapter: Optional[Dict[str, Any]] = None):
        """Handle audiobook selection"""
        if not chapter and audiobook.chapters:
            chapter = audiobook.chapters[0]

        self.audiobook_selected.emit(audiobook, chapter or {})

    def _on_search_text_changed(self, text: str):
        """Handle search text change"""
        self.search_requested.emit(text)

    def set_current_library(self, library_id: str):
        """Set current library"""
        self._current_library = library_id

    def set_audiobooks(self, audiobooks: List[Audiobook]):
        """Set audiobooks to display"""
        self._audiobooks = audiobooks
