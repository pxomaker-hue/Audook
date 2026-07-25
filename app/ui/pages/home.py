"""
Home page - displaying library and recommendations
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
                             QGridLayout, QLineEdit, QPushButton)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from app.ui.widgets import BookCard
from app.services import LibraryService


class HomePage(QWidget):
    """Home page with library and recommendations"""

    book_selected = pyqtSignal(str)  # Emits book_id
    sync_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_books = []
        self.init_ui()
        self.load_books()

    def init_ui(self):
        """Initialize home page UI"""
        self.setObjectName("content_area")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 32, 32, 32)
        main_layout.setSpacing(24)

        # Header section
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)

        title = QLabel("My Library")
        title.setObjectName("title")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Search box
        self.search = QLineEdit()
        self.search.setObjectName("search_box")
        self.search.setPlaceholderText("Search books...")
        self.search.setMaximumWidth(300)
        self.search.setStyleSheet("""
            QLineEdit {
                background-color: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #cccccc;
                background-color: #ffffff;
            }
        """)
        self.search.textChanged.connect(self.on_search)
        header_layout.addWidget(self.search)

        # Sync button
        sync_btn = QPushButton("⟳ Sync")
        sync_btn.setObjectName("primary_btn")
        sync_btn.setMaximumWidth(100)
        sync_btn.setStyleSheet("""
            QPushButton {
                background-color: #000000;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #333333;
            }
        """)
        sync_btn.clicked.connect(self.sync_requested.emit)
        header_layout.addWidget(sync_btn)

        main_layout.addLayout(header_layout)

        # Books grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(24)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        # Books will be loaded from database
        self.book_cards = []

        # Add stretch at the end
        self.grid_layout.setRowStretch(self.grid_layout.rowCount(), 1)
        self.grid_layout.setColumnStretch(self.grid_layout.columnCount(), 1)

        scroll_area.setWidget(self.grid_widget)

        main_layout.addWidget(scroll_area)

    def load_books(self, books=None):
        """Load books from database"""
        if books is None:
            books = LibraryService.get_all_books()

        self.current_books = books

        # Clear existing cards
        while self.grid_layout.count() > 0:
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.book_cards = []

        # Add books to grid
        col = 0
        row = 0
        for audiobook in books:
            card = BookCard(
                audiobook.id,
                audiobook.title,
                audiobook.author or "Unknown",
                rating=4.0  # TODO: Get rating from metadata
            )
            card.play_clicked.connect(self.on_book_play)
            card.cover_clicked.connect(self.on_book_click)
            self.grid_layout.addWidget(card, row, col)

            self.book_cards.append(card)

            col += 1
            if col >= 4:
                col = 0
                row += 1

        # Add stretch at the end
        self.grid_layout.setRowStretch(row + 1, 1)
        self.grid_layout.setColumnStretch(4, 1)

    def on_search(self, query: str):
        """Handle search query"""
        if not query:
            self.load_books()
        else:
            results = LibraryService.search_books(query)
            self.load_books(results)

    def on_book_click(self, book_id: str):
        """Handle book click"""
        self.book_selected.emit(book_id)

    def on_book_play(self, book_id: str):
        """Handle play button click"""
        self.book_selected.emit(book_id)
