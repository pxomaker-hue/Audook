"""
Player widget displaying now playing info and controls
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSlider
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class PlayerWidget(QWidget):
    """Compact player widget with controls"""

    play_pause = pyqtSignal()
    prev_track = pyqtSignal()
    next_track = pyqtSignal()
    seek = pyqtSignal(int)  # Position in seconds
    volume_changed = pyqtSignal(int)  # Volume 0-100

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_playing = False
        self.current_position = 0
        self.duration = 0
        self.init_ui()

    def init_ui(self):
        """Initialize player UI"""
        self.setObjectName("player_bar")
        self.setMinimumHeight(80)
        self.setStyleSheet("""
            QWidget#player_bar {
                background-color: #ffffff;
                border-top: 1px solid #e0e0e0;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(8)

        # Now playing info
        info_layout = QHBoxLayout()
        info_layout.setSpacing(12)

        # Cover thumbnail
        cover_label = QLabel("📖")
        cover_label.setStyleSheet("font-size: 28px;")
        cover_label.setMinimumSize(48, 48)
        cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                border-radius: 4px;
                font-size: 24px;
            }
        """)
        info_layout.addWidget(cover_label)

        # Title and artist
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        self.title_label = QLabel("No book selected")
        self.title_label.setStyleSheet("color: #000000; font-size: 13px; font-weight: 600;")
        text_layout.addWidget(self.title_label)

        self.artist_label = QLabel("Unknown Author")
        self.artist_label.setStyleSheet("color: #666666; font-size: 12px;")
        text_layout.addWidget(self.artist_label)

        info_layout.addLayout(text_layout)
        info_layout.addStretch()

        main_layout.addLayout(info_layout)

        # Progress bar
        progress_layout = QHBoxLayout()
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(8)

        self.time_current = QLabel("0:00")
        self.time_current.setObjectName("time_label")
        self.time_current.setStyleSheet("color: #999999; font-size: 12px; min-width: 30px;")
        progress_layout.addWidget(self.time_current)

        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.sliderMoved.connect(self.on_slider_moved)
        progress_layout.addWidget(self.progress_slider)

        self.time_total = QLabel("0:00")
        self.time_total.setObjectName("time_label")
        self.time_total.setStyleSheet("color: #999999; font-size: 12px; min-width: 30px;")
        progress_layout.addWidget(self.time_total)

        main_layout.addLayout(progress_layout)

        # Controls
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(12)

        # Previous button
        prev_btn = QPushButton("⏮")
        prev_btn.setObjectName("icon_btn")
        prev_btn.setMaximumWidth(40)
        prev_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 16px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-radius: 4px;
            }
        """)
        prev_btn.clicked.connect(self.prev_track.emit)
        controls_layout.addWidget(prev_btn)

        # Play/Pause button
        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("primary_btn")
        self.play_btn.setMinimumSize(48, 48)
        self.play_btn.setMaximumSize(48, 48)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #000000;
                color: #ffffff;
                border: none;
                border-radius: 24px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #333333;
            }
        """)
        self.play_btn.clicked.connect(self.on_play_pause_clicked)
        controls_layout.addWidget(self.play_btn)

        # Next button
        next_btn = QPushButton("⏭")
        next_btn.setObjectName("icon_btn")
        next_btn.setMaximumWidth(40)
        next_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 16px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-radius: 4px;
            }
        """)
        next_btn.clicked.connect(self.next_track.emit)
        controls_layout.addWidget(next_btn)

        controls_layout.addStretch()

        # Volume control
        volume_btn = QPushButton("🔊")
        volume_btn.setObjectName("icon_btn")
        volume_btn.setMaximumWidth(30)
        volume_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 14px;
                padding: 4px;
            }
        """)
        controls_layout.addWidget(volume_btn)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setMaximumWidth(100)
        self.volume_slider.sliderMoved.connect(lambda v: self.volume_changed.emit(v))
        controls_layout.addWidget(self.volume_slider)

        main_layout.addLayout(controls_layout)

    def on_play_pause_clicked(self):
        """Handle play/pause button click"""
        self.is_playing = not self.is_playing
        self.update_play_button()
        self.play_pause.emit()

    def update_play_button(self):
        """Update play/pause button icon"""
        self.play_btn.setText("⏸" if self.is_playing else "▶")

    def on_slider_moved(self, position):
        """Handle seek slider movement"""
        if self.duration > 0:
            seconds = int((position / 100.0) * self.duration)
            self.seek.emit(seconds)

    def set_now_playing(self, title: str, artist: str):
        """Update now playing information"""
        self.title_label.setText(title)
        self.artist_label.setText(artist)

    def update_progress(self, current_ms: int, duration_ms: int):
        """Update progress bar"""
        self.current_position = current_ms / 1000
        self.duration = duration_ms / 1000

        # Update time labels
        self.time_current.setText(self._format_time(self.current_position))
        self.time_total.setText(self._format_time(self.duration))

        # Update slider
        if self.duration > 0:
            progress = int((self.current_position / self.duration) * 100)
            self.progress_slider.blockSignals(True)
            self.progress_slider.setValue(progress)
            self.progress_slider.blockSignals(False)

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds to MM:SS"""
        if not seconds or seconds < 0:
            return "0:00"
        mins = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{mins}:{secs:02d}"
