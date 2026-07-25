"""
Player view - Modern audiobook player interface
"""

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider,
    QLabel, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QPixmap
from pathlib import Path

from app.models import Audiobook
from app.utils.cover_generator import get_or_create_cover
from app.utils import format_duration


class PlayerView(QWidget):
    """Modern player view for audiobook playback"""

    play_pause_clicked = pyqtSignal()
    previous_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    seek_backward_clicked = pyqtSignal(int)
    seek_forward_clicked = pyqtSignal(int)
    volume_changed = pyqtSignal(float)
    speed_changed = pyqtSignal(float)
    position_changed = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self._audiobook: Optional[Audiobook] = None
        self._chapter: Optional[Dict[str, Any]] = None
        self._current_position: float = 0.0
        self._is_playing: bool = False
        self._init_ui()

        # Update timer
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._on_update)
        self._update_timer.start(100)

    def _init_ui(self):
        """Initialize UI"""
        self.setStyleSheet("""
            PlayerView {
                background-color: #0d1117;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Now Playing Section
        now_playing = QLabel("En cours de lecture")
        now_playing.setFont(QFont("Segoe UI", 10))
        now_playing.setStyleSheet("color: #888;")
        layout.addWidget(now_playing)

        # Cover and Info Layout
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # Cover Image
        self._cover_label = QLabel()
        self._cover_label.setFixedSize(120, 160)
        self._cover_label.setStyleSheet("""
            QLabel {
                background-color: #1a2332;
                border-radius: 8px;
                border: 1px solid #2a3f5f;
            }
        """)
        self._cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self._cover_label)

        # Info Section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)

        # Title
        self._title_label = QLabel("Aucun audiobook sélectionné")
        self._title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self._title_label.setWordWrap(True)
        self._title_label.setStyleSheet("color: #fff;")
        info_layout.addWidget(self._title_label)

        # Author
        self._author_label = QLabel("")
        self._author_label.setFont(QFont("Segoe UI", 11))
        self._author_label.setStyleSheet("color: #aaa;")
        info_layout.addWidget(self._author_label)

        # Chapter
        self._chapter_label = QLabel("")
        self._chapter_label.setFont(QFont("Segoe UI", 10))
        self._chapter_label.setStyleSheet("color: #888;")
        info_layout.addWidget(self._chapter_label)

        info_layout.addStretch()

        # Position info
        position_layout = QHBoxLayout()

        self._position_label = QLabel("00:00")
        self._position_label.setFont(QFont("Segoe UI Mono", 10))
        self._position_label.setStyleSheet("color: #4a7fa5;")
        position_layout.addWidget(self._position_label)

        self._duration_label = QLabel("00:00")
        self._duration_label.setFont(QFont("Segoe UI Mono", 10))
        self._duration_label.setStyleSheet("color: #888;")
        position_layout.addWidget(self._duration_label)

        info_layout.addLayout(position_layout)

        content_layout.addLayout(info_layout)
        content_layout.addStretch()

        layout.addLayout(content_layout)

        # Progress bar
        self._progress_slider = QSlider(Qt.Orientation.Horizontal)
        self._progress_slider.setMinimum(0)
        self._progress_slider.setMaximum(100)
        self._progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background-color: #1a2332;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 14px;
                margin: -4px 0;
                background-color: #4a7fa5;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background-color: #5a9fcd;
            }
        """)
        layout.addWidget(self._progress_slider)

        # Controls Section
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)

        # Volume
        volume_layout = QHBoxLayout()
        volume_layout.setSpacing(6)

        volume_icon = QLabel("🔊")
        volume_layout.addWidget(volume_icon)

        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setMinimum(0)
        self._volume_slider.setMaximum(100)
        self._volume_slider.setValue(80)
        self._volume_slider.setMaximumWidth(100)
        self._volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background-color: #1a2332;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 10px;
                margin: -3px 0;
                background-color: #4a7fa5;
                border-radius: 5px;
            }
        """)
        self._volume_slider.valueChanged.connect(self._on_volume_changed)
        volume_layout.addWidget(self._volume_slider)

        controls_layout.addLayout(volume_layout)
        controls_layout.addStretch()

        # Playback Controls
        button_style = """
            QPushButton {
                background-color: #2a3f5f;
                border: 1px solid #3a5f7f;
                border-radius: 6px;
                color: #fff;
                padding: 8px 12px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3a5f7f;
                border: 1px solid #4a7fa5;
            }
            QPushButton:pressed {
                background-color: #4a7fa5;
            }
        """

        play_button_style = """
            QPushButton {
                background-color: #4a7fa5;
                border: 1px solid #5a9fcd;
                border-radius: 6px;
                color: #fff;
                padding: 10px 14px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #5a9fcd;
            }
            QPushButton:pressed {
                background-color: #6aafd5;
            }
        """

        # Back 10s
        self._back_10_btn = QPushButton("⏪ 10s")
        self._back_10_btn.setStyleSheet(button_style)
        self._back_10_btn.clicked.connect(lambda: self.seek_backward_clicked.emit(10))
        controls_layout.addWidget(self._back_10_btn)

        # Previous chapter
        self._prev_chapter_btn = QPushButton("⏮ Précédent")
        self._prev_chapter_btn.setStyleSheet(button_style)
        self._prev_chapter_btn.clicked.connect(self.previous_clicked.emit)
        controls_layout.addWidget(self._prev_chapter_btn)

        # Play/Pause
        self._play_pause_btn = QPushButton("▶")
        self._play_pause_btn.setMaximumWidth(60)
        self._play_pause_btn.setStyleSheet(play_button_style)
        self._play_pause_btn.clicked.connect(self._on_play_pause)
        controls_layout.addWidget(self._play_pause_btn)

        # Next chapter
        self._next_chapter_btn = QPushButton("Suivant ⏭")
        self._next_chapter_btn.setStyleSheet(button_style)
        self._next_chapter_btn.clicked.connect(self.next_clicked.emit)
        controls_layout.addWidget(self._next_chapter_btn)

        # Forward 10s
        self._forward_10_btn = QPushButton("10s ⏩")
        self._forward_10_btn.setStyleSheet(button_style)
        self._forward_10_btn.clicked.connect(lambda: self.seek_forward_clicked.emit(10))
        controls_layout.addWidget(self._forward_10_btn)

        layout.addLayout(controls_layout)
        layout.addStretch()

    def set_audiobook(self, audiobook: Audiobook, chapter: Dict[str, Any]):
        """Set the audiobook to display"""
        self._audiobook = audiobook
        self._chapter = chapter

        # Update cover
        try:
            covers_dir = Path("app/assets/covers")
            covers_dir.mkdir(parents=True, exist_ok=True)

            cover_path = get_or_create_cover(audiobook.id, audiobook.title, audiobook.author, covers_dir)
            pixmap = QPixmap(str(cover_path))
            if not pixmap.isNull():
                pixmap = pixmap.scaledToWidth(120, Qt.TransformationMode.SmoothTransformation)
                self._cover_label.setPixmap(pixmap)
        except Exception as e:
            print(f"Error loading cover: {e}")

        # Update text
        self._title_label.setText(audiobook.title)
        self._author_label.setText(audiobook.author)

        if chapter:
            self._chapter_label.setText(f"Chapitre: {chapter.get('title', 'Inconnu')}")
            duration = chapter.get('duration', 0)
            self._progress_slider.setMaximum(int(duration))
            self._duration_label.setText(format_duration(duration))

    def set_position(self, position: float):
        """Update player position"""
        self._current_position = position
        self._progress_slider.blockSignals(True)
        self._progress_slider.setValue(int(position))
        self._progress_slider.blockSignals(False)
        self._position_label.setText(format_duration(position))

    def set_playing(self, is_playing: bool):
        """Update play button state"""
        self._is_playing = is_playing
        self._play_pause_btn.setText("⏸" if is_playing else "▶")

    def get_current_audiobook(self) -> Optional[Audiobook]:
        """Get current audiobook"""
        return self._audiobook

    def get_current_chapter(self) -> Optional[Dict[str, Any]]:
        """Get current chapter"""
        return self._chapter

    def _on_play_pause(self):
        """Handle play/pause button"""
        self.play_pause_clicked.emit()

    def _on_volume_changed(self, value: int):
        """Handle volume change"""
        volume = value / 100.0
        self.volume_changed.emit(volume)

    def _on_update(self):
        """Update player display"""
        pass
        return self._chapter
