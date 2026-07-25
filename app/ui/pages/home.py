"""
Home page - displaying library and recommendations
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
                             QGridLayout, QLineEdit, QPushButton)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from app.ui.widgets import BookCard


class HomePage(QWidget):
    """Home page with library and recommendations"""

    book_selected = pyqtSignal(str)  # Emits book_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

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
        search = QLineEdit()
        search.setObjectName("search_box")
        search.setPlaceholderText("Search books...")
        search.setMaximumWidth(300)
        search.setStyleSheet("""
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
        header_layout.addWidget(search)

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
        header_layout.addWidget(sync_btn)

        main_layout.addLayout(header_layout)

        # Books grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(24)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        # Sample books (will be populated from database)
        self.books = []
        self._add_sample_books(grid_layout)

        # Add stretch at the end
        grid_layout.setRowStretch(grid_layout.rowCount(), 1)
        grid_layout.setColumnStretch(grid_layout.columnCount(), 1)

        scroll_area.setWidget(grid_widget)

        main_layout.addWidget(scroll_area)

    def _add_sample_books(self, layout):
        """Add sample books to grid for demo"""
        sample_books = [
            ("book_1", "The Great Gatsby", "F. Scott Fitzgerald", 4.5),
            ("book_2", "The Hobbit", "J.R.R. Tolkien", 4.7),
            ("book_3", "1984", "George Orwell", 4.3),
            ("book_4", "Pride and Prejudice", "Jane Austen", 4.6),
            ("book_5", "The Catcher in the Rye", "J.D. Salinger", 4.2),
            ("book_6", "Moby Dick", "Herman Melville", 3.8),
        ]

        col = 0
        row = 0
        for book_id, title, author, rating in sample_books:
            card = BookCard(book_id, title, author, rating)
            card.play_clicked.connect(self.on_book_play)
            card.cover_clicked.connect(self.on_book_click)
            layout.addWidget(card, row, col)

            self.books.append(card)

            col += 1
            if col >= 4:
                col = 0
                row += 1

    def on_book_click(self, book_id: str):
        """Handle book click"""
        self.book_selected.emit(book_id)

    def on_book_play(self, book_id: str):
        """Handle play button click"""
        self.book_selected.emit(book_id)

    def load_books_from_db(self, books):
        """Load books from database"""
        # This will be connected to database queries
        pass
