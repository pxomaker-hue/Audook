"""
Explore page - search and discover audiobooks
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QScrollArea, QGridLayout, QPushButton)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from app.ui.widgets import BookCard


class ExplorePage(QWidget):
    """Explore page for discovering audiobooks"""

    book_selected = pyqtSignal(str)  # Emits book_id
    search_query = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize explore page UI"""
        self.setObjectName("content_area")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 32, 32, 32)
        main_layout.setSpacing(24)

        # Header with search
        header_layout = QVBoxLayout()
        header_layout.setSpacing(16)

        title = QLabel("Explore")
        title.setObjectName("title")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        header_layout.addWidget(title)

        # Search box
        search = QLineEdit()
        search.setObjectName("search_box")
        search.setPlaceholderText("Search books...")
        search.setMinimumHeight(44)
        search.setMaximumWidth(500)
        search.setStyleSheet("""
            QLineEdit {
                background-color: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #cccccc;
                background-color: #ffffff;
            }
        """)
        search.textChanged.connect(lambda text: self.search_query.emit(text))
        header_layout.addWidget(search)

        main_layout.addLayout(header_layout)

        # Featured section
        featured_title = QLabel("Book of the Day")
        featured_title.setObjectName("section_title")
        section_font = QFont()
        section_font.setPointSize(16)
        section_font.setBold(True)
        featured_title.setFont(section_font)
        main_layout.addWidget(featured_title)

        featured_layout = QHBoxLayout()
        featured_layout.setSpacing(32)

        # Featured book card (larger)
        featured_card = QWidget()
        featured_card_layout = QVBoxLayout(featured_card)
        featured_card_layout.setSpacing(16)
        featured_card_layout.setContentsMargins(0, 0, 0, 0)

        featured_cover = QPushButton()
        featured_cover.setMinimumSize(200, 300)
        featured_cover.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: none;
                border-radius: 12px;
                font-size: 80px;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
            }
        """)
        featured_cover.setText("📖")
        featured_card_layout.addWidget(featured_cover)

        featured_card_layout.addStretch()

        featured_layout.addWidget(featured_card)

        # Featured book info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(12)

        featured_book_title = QLabel("The Great Gatsby")
        featured_book_title.setStyleSheet("color: #000000; font-size: 18px; font-weight: 600;")
        info_layout.addWidget(featured_book_title)

        featured_author = QLabel("F. Scott Fitzgerald")
        featured_author.setStyleSheet("color: #666666; font-size: 14px;")
        info_layout.addWidget(featured_author)

        featured_desc = QLabel(
            "A classic novel of the Jazz Age that explores themes of wealth, love, and the American Dream."
        )
        featured_desc.setWordWrap(True)
        featured_desc.setStyleSheet("color: #666666; font-size: 13px; line-height: 1.5;")
        info_layout.addWidget(featured_desc)

        featured_rating = QLabel("★★★★★ 4.5")
        featured_rating.setStyleSheet("color: #ffc107; font-size: 13px;")
        info_layout.addWidget(featured_rating)

        info_layout.addSpacing(12)

        read_btn = QPushButton("Start Listening")
        read_btn.setObjectName("primary_btn")
        read_btn.setMaximumWidth(200)
        read_btn.setStyleSheet("""
            QPushButton {
                background-color: #000000;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #333333;
            }
        """)
        info_layout.addWidget(read_btn)

        info_layout.addStretch()

        featured_layout.addLayout(info_layout)

        main_layout.addLayout(featured_layout)

        # Recommended section
        main_layout.addSpacing(24)

        rec_title = QLabel("Recommended for You")
        rec_title.setObjectName("section_title")
        rec_title.setFont(section_font)
        main_layout.addWidget(rec_title)

        # Recommended books grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(24)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        # Sample recommended books
        recommended = [
            ("book_1", "The Hobbit", "J.R.R. Tolkien", 4.7),
            ("book_2", "1984", "George Orwell", 4.3),
            ("book_3", "Pride and Prejudice", "Jane Austen", 4.6),
            ("book_4", "Moby Dick", "Herman Melville", 3.8),
        ]

        col = 0
        for book_id, title, author, rating in recommended:
            card = BookCard(book_id, title, author, rating)
            card.play_clicked.connect(self.on_book_play)
            card.cover_clicked.connect(self.on_book_click)
            grid_layout.addWidget(card, 0, col)
            col += 1

        # Add stretch
        grid_layout.setColumnStretch(col, 1)
        scroll_area.setWidget(grid_widget)

        main_layout.addWidget(scroll_area)

    def on_book_click(self, book_id: str):
        """Handle book click"""
        self.book_selected.emit(book_id)

    def on_book_play(self, book_id: str):
        """Handle play button click"""
        self.book_selected.emit(book_id)
