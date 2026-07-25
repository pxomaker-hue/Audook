"""
Book card widget for displaying audiobook information
Shows cover, title, author, rating, and play button
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt, pyqtSignal
from pathlib import Path


class BookCard(QWidget):
    """Card displaying a single audiobook"""

    play_clicked = pyqtSignal(str)  # Emits book_id
    cover_clicked = pyqtSignal(str)  # Emits book_id

    def __init__(self, book_id: str, title: str, author: str, rating: float = 0.0,
                 cover_url: str = None, parent=None):
        super().__init__(parent)
        self.book_id = book_id
        self.title_text = title
        self.author_text = author
        self.rating = rating
        self.cover_url = cover_url

        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        self.setObjectName("book_card")
        self.setMinimumSize(180, 300)
        self.setMaximumWidth(200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Cover image
        cover_btn = QPushButton()
        cover_btn.setObjectName("icon_btn")
        cover_btn.setMinimumHeight(200)
        cover_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
            }
        """)

        if self.cover_url:
            pixmap = QPixmap(self.cover_url)
            if not pixmap.isNull():
                pixmap = pixmap.scaledToWidth(180, Qt.TransformationMode.SmoothTransformation)
                cover_btn.setIcon(pixmap)
                cover_btn.setIconSize(pixmap.size())
            else:
                cover_btn.setText("📖")
        else:
            cover_btn.setText("📖")
            font = QFont()
            font.setPointSize(48)
            cover_btn.setFont(font)

        cover_btn.clicked.connect(lambda: self.cover_clicked.emit(self.book_id))
        layout.addWidget(cover_btn)

        # Info section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)

        # Title
        title_label = QLabel(self.title_text)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("color: #000000; font-size: 13px; font-weight: 600;")
        info_layout.addWidget(title_label)

        # Author
        author_label = QLabel(self.author_text)
        author_label.setStyleSheet("color: #666666; font-size: 12px;")
        author_label.setWordWrap(True)
        info_layout.addWidget(author_label)

        # Rating
        if self.rating > 0:
            rating_text = "★" * int(self.rating) + "☆" * (5 - int(self.rating))
            rating_label = QLabel(rating_text)
            rating_label.setObjectName("rating")
            rating_label.setStyleSheet("color: #ffc107; font-size: 11px;")
            info_layout.addWidget(rating_label)

        layout.addLayout(info_layout)

        # Play button
        play_btn = QPushButton("Play")
        play_btn.setObjectName("primary_btn")
        play_btn.setStyleSheet("""
            QPushButton {
                background-color: #000000;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #333333;
            }
        """)
        play_btn.clicked.connect(lambda: self.play_clicked.emit(self.book_id))
        layout.addWidget(play_btn)

        layout.addStretch()

    def set_cover_from_url(self, url: str):
        """Load and display cover from URL"""
        self.cover_url = url
        # In production, would download from URL
        # For now, relies on local file path
