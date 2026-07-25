"""
Library view for Audook
Displays the audiobook library and allows browsing
"""

from PyQt6.QtWidgets import (
 QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
 QListWidgetItem, QPushButton, QLineEdit, QComboBox,
 QFrame, QToolButton, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint
from PyQt6.QtGui import QIcon, QPixmap, QFont, QAction
from typing import List, Optional, Dict, Any

from app.models import Audiobook, Library
from app.utils import format_duration


class AudiobookItemWidget(QWidget):
 """Widget for displaying an audiobook in the list"""
 
 def __init__(self, audiobook: Audiobook, parent=None):
 super().__init__(parent)
 self.audiobook = audiobook
 self._init_ui()
 
 def _init_ui(self):
 """Initialize UI"""
 layout = QHBoxLayout(self)
 layout.setContentsMargins(10, 10, 10, 10)
 layout.setSpacing(15)
 
 # Cover
 self._cover_label = QLabel()
 self._cover_label.setFixedSize(60, 60)
 self._cover_label.setStyleSheet(
 "background-color: #0f3460; border-radius: 8px;"
 )
 self._cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
 self._cover_label.setText("📖")
 self._cover_label.setFont(QFont("Segoe UI", 24))
 
 # Info
 info_layout = QVBoxLayout()
 info_layout.setSpacing(2)
 
 self._title_label = QLabel(self.audiobook.title)
 self._title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
 self._title_label.setStyleSheet("color: #eaeaea;")
 
 self._author_label = QLabel(self.audiobook.author)
 self._author_label.setFont(QFont("Segoe UI", 12))
 self._author_label.setStyleSheet("color: #888888;")
 
 self._meta_label = QLabel()
 self._meta_label.setFont(QFont("Segoe UI", 10))
 self._meta_label.setStyleSheet("color: #666666;")
 self._update_meta()
 
 info_layout.addWidget(self._title_label)
 info_layout.addWidget(self._author_label)
 info_layout.addWidget(self._meta_label)
 
 # Duration
 self._duration_label = QLabel(format_duration(self.audiobook.duration))
 self._duration_label.setFont(QFont("Segoe UI", 12))
 self._duration_label.setStyleSheet("color: #888888;")
 self._duration_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
 
 layout.addWidget(self._cover_label)
 layout.addLayout(info_layout)
 layout.addStretch()
 layout.addWidget(self._duration_label)
 
 self.setStyleSheet("""
 AudiobookItemWidget {
 background-color: #16213e;
 border-radius: 8px;
 }
 AudiobookItemWidget:hover {
 background-color: #1a2a4a;
 }
 """)
 
 def _update_meta(self):
 """Update metadata label"""
 parts = []
 if self.audiobook.narrator:
 parts.append(f"Narrated by {self.audiobook.narrator}")
 if self.audiobook.duration > 0:
 parts.append(f"{format_duration(self.audiobook.duration)}")
 
 if len(self.audiobook.chapters) > 0:
 parts.append(f"{len(self.audiobook.chapters)} chapters")
 
 self._meta_label.setText(" | ".join(parts))


class LibraryView(QWidget):
 """Library view widget"""
 
 # Signals
 audiobook_selected = pyqtSignal(Audiobook, dict) # audiobook, chapter
 audiobook_double_clicked = pyqtSignal(Audiobook)
 library_changed = pyqtSignal(str) # library_id
 server_changed = pyqtSignal(str) # server_id
 refresh_requested = pyqtSignal()
 search_requested = pyqtSignal(str)
 download_requested = pyqtSignal(Audiobook)
 
 def __init__(self, parent=None):
 super().__init__(parent)
 self._audiobooks: List[Audiobook] = []
 self._libraries: List[Library] = []
 self._current_library_id: Optional[str] = None
 self._current_server_id: Optional[str] = None
 
 self._init_ui()
 self._setup_connections()
 
 def _init_ui(self):
 """Initialize UI"""
 layout = QVBoxLayout(self)
 layout.setContentsMargins(15, 15, 15, 15)
 layout.setSpacing(15)
 
 # Header with controls
 header_frame = QFrame()
 header_layout = QHBoxLayout(header_frame)
 header_layout.setContentsMargins(10, 10, 10, 10)
 header_layout.setSpacing(10)
 
 # Server selector
 self._server_combo = QComboBox()
 self._server_combo.setFixedWidth(200)
 self._server_combo.setStyleSheet("""
 QComboBox {
 background-color: #0f3460;
 color: #eaeaea;
 border: 1px solid #1a4a7a;
 border-radius: 6px;
 padding: 8px 12px;
 }
 """)
 
 # Library selector
 self._library_combo = QComboBox()
 self._library_combo.setFixedWidth(200)
 self._library_combo.setStyleSheet("""
 QComboBox {
 background-color: #0f3460;
 color: #eaeaea;
 border: 1px solid #1a4a7a;
 border-radius: 6px;
 padding: 8px 12px;
 }
 """)
 
 # Search
 self._search_edit = QLineEdit()
 self._search_edit.setPlaceholderText("Search audiobooks...")
 self._search_edit.setFixedWidth(250)
 self._search_edit.setStyleSheet("""
 QLineEdit {
 background-color: #0f3460;
 color: #eaeaea;
 border: 1px solid #1a4a7a;
 border-radius: 6px;
 padding: 8px 12px;
 }
 """)
 
 # Refresh button
 self._refresh_button = QToolButton()
 self._refresh_button.setText("🔄")
 self._refresh_button.setToolTip("Refresh")
 self._refresh_button.setFixedSize(40, 40)
 self._refresh_button.setStyleSheet("""
 QToolButton {
 background-color: #0f3460;
 border-radius: 20px;
 font-size: 16px;
 }
 QToolButton:hover {
 background-color: #1a4a7a;
 }
 """)
 
 header_layout.addWidget(self._server_combo)
 header_layout.addWidget(self._library_combo)
 header_layout.addStretch()
 header_layout.addWidget(self._search_edit)
 header_layout.addWidget(self._refresh_button)
 
 # Audiobook list
 self._audiobook_list = QListWidget()
 self._audiobook_list.setIconSize(QSize(60, 60))
 self._audiobook_list.setSpacing(5)
 self._audiobook_list.setStyleSheet("""
 QListWidget {
 background-color: #0f3460;
 border: 1px solid #1a4a7a;
 border-radius: 8px;
 padding: 5px;
 }
 QListWidget::item {
 padding: 0;
 border-radius: 8px;
 }
 QListWidget::item:selected {
 background-color: #e94560;
 border-radius: 8px;
 }
 """)
 
 # Set item widget size
 self._audiobook_list.setItemDelegate(ItemDelegate(self))
 
 # Status bar
 self._status_label = QLabel("Ready")
 self._status_label.setFont(QFont("Segoe UI", 12))
 self._status_label.setStyleSheet("color: #888888;")
 
 layout.addWidget(header_frame)
 layout.addWidget(self._audiobook_list)
 layout.addWidget(self._status_label)
 
 # Context menu
 self._audiobook_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
 
 def _setup_connections(self):
 """Setup signal connections"""
 self._server_combo.currentIndexChanged.connect(self._on_server_changed)
 self._library_combo.currentIndexChanged.connect(self._on_library_changed)
 self._search_edit.textChanged.connect(self._on_search_changed)
 self._search_edit.returnPressed.connect(self._on_search_enter)
 self._refresh_button.clicked.connect(self._on_refresh_clicked)
 self._audiobook_list.itemClicked.connect(self._on_item_clicked)
 self._audiobook_list.itemDoubleClicked.connect(self._on_item_double_clicked)
 self._audiobook_list.customContextMenuRequested.connect(self._on_context_menu)
 
 def _on_server_changed(self, index: int):
 """Handle server selection change"""
 if index >= 0 and index < self._server_combo.count():
 server_id = self._server_combo.itemData(index)
 self.server_changed.emit(server_id)
 
 def _on_library_changed(self, index: int):
 """Handle library selection change"""
 if index >= 0 and index < self._library_combo.count():
 library_id = self._library_combo.itemData(index)
 self.library_changed.emit(library_id)
 
 def _on_search_changed(self, text: str):
 """Handle search text change"""
 if len(text) >= 2:
 self.search_requested.emit(text)
 elif len(text) == 0:
 self.search_requested.emit("")
 
 def _on_search_enter(self):
 """Handle search enter key"""
 text = self._search_edit.text()
 if text:
 self.search_requested.emit(text)
 
 def _on_refresh_clicked(self):
 """Handle refresh button click"""
 self.refresh_requested.emit()
 
 def _on_item_clicked(self, item: QListWidgetItem):
 """Handle item click"""
 widget = self._audiobook_list.itemWidget(item)
 if widget and isinstance(widget, AudiobookItemWidget):
 audiobook = widget.audiobook
 # Select first chapter
 if audiobook.chapters:
 chapter = audiobook.chapters[0]
 self.audiobook_selected.emit(audiobook, chapter)
 
 def _on_item_double_clicked(self, item: QListWidgetItem):
 """Handle item double click"""
 widget = self._audiobook_list.itemWidget(item)
 if widget and isinstance(widget, AudiobookItemWidget):
 self.audiobook_double_clicked.emit(widget.audiobook)
 
 def _on_context_menu(self, pos: QPoint):
 """Handle context menu request"""
 item = self._audiobook_list.itemAt(pos)
 if not item:
 return
 
 widget = self._audiobook_list.itemWidget(item)
 if not widget or not isinstance(widget, AudiobookItemWidget):
 return
 
 audiobook = widget.audiobook
 
 menu = QMenu(self)
 
 # Play action
 play_action = QAction("Play", menu)
 play_action.triggered.connect(lambda: self._play_audiobook(audiobook))
 menu.addAction(play_action)
 
 # Download action
 download_action = QAction("Download", menu)
 download_action.triggered.connect(lambda: self.download_requested.emit(audiobook))
 menu.addAction(download_action)
 
 # Info action
 info_action = QAction("Info", menu)
 info_action.triggered.connect(lambda: self._show_info(audiobook))
 menu.addAction(info_action)
 
 menu.exec(self._audiobook_list.viewport().mapToGlobal(pos))
 
 def _play_audiobook(self, audiobook: Audiobook):
 """Play an audiobook"""
 if audiobook.chapters:
 chapter = audiobook.chapters[0]
 self.audiobook_selected.emit(audiobook, chapter)
 
 def _show_info(self, audiobook: Audiobook):
 """Show audiobook info"""
 # For now, just show in status
 self._status_label.setText(f"{audiobook.title} - {audiobook.author}")
 
 # Public methods
 def set_servers(self, servers: List[Dict[str, Any]]):
 """Set available servers"""
 self._server_combo.clear()
 for server in servers:
 self._server_combo.addItem(server.get("name", "Unknown"), server.get("id"))
 
 def set_libraries(self, libraries: List[Library]):
 """Set available libraries"""
 self._libraries = libraries
 self._library_combo.clear()
 for library in libraries:
 self._library_combo.addItem(library.name, library.id)
 
 def set_audiobooks(self, audiobooks: List[Audiobook]):
 """Set audiobooks to display"""
 self._audiobooks = audiobooks
 self._audiobook_list.clear()
 
 for audiobook in audiobooks:
 item = QListWidgetItem()
 item.setSizeHint(QSize(100, 80))
 
 widget = AudiobookItemWidget(audiobook)
 
 self._audiobook_list.addItem(item)
 self._audiobook_list.setItemWidget(item, widget)
 
 self._status_label.setText(f"{len(audiobooks)} audiobooks")
 
 def set_current_server(self, server_id: str):
 """Set current server"""
 self._current_server_id = server_id
 index = self._server_combo.findData(server_id)
 if index >= 0:
 self._server_combo.setCurrentIndex(index)
 
 def set_current_library(self, library_id: str):
 """Set current library"""
 self._current_library_id = library_id
 index = self._library_combo.findData(library_id)
 if index >= 0:
 self._library_combo.setCurrentIndex(index)
 
 def set_status(self, message: str):
 """Set status message"""
 self._status_label.setText(message)
 
 def clear_selection(self):
 """Clear selection"""
 self._audiobook_list.clearSelection()


class ItemDelegate(QWidget):
 """Custom item delegate for proper sizing"""
 
 def __init__(self, parent=None):
 super().__init__(parent)
 
 def sizeHint(self, option, index):
 return QSize(100, 80)
