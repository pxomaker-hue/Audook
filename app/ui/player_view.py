"""
Player view for Audook
Displays the current playback information and controls
"""

from PyQt6.QtWidgets import (
 QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
 QSlider, QFrame, QToolButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QFont
from typing import Optional
import os

from app.models import Audiobook
from app.player.player import player
from app.utils import format_duration
from app.ui import get_stylesheet


class PlayerView(QWidget):
 """Player view widget"""
 
 # Signals
 play_pause_clicked = pyqtSignal()
 previous_clicked = pyqtSignal()
 next_clicked = pyqtSignal()
 seek_backward_clicked = pyqtSignal(int) # seconds
 seek_forward_clicked = pyqtSignal(int) # seconds
 volume_changed = pyqtSignal(float)
 speed_changed = pyqtSignal(float)
 
 def __init__(self, parent=None):
 super().__init__(parent)
 self._audiobook: Optional[Audiobook] = None
 self._chapter: Optional[dict] = None
 self._updating_slider = False
 
 self._init_ui()
 self._setup_connections()
 self._update_timer = QTimer(self)
 self._update_timer.timeout.connect(self._update_playback_info)
 self._update_timer.start(100)
 
 def _init_ui(self):
 """Initialize UI components"""
 # Main layout
 layout = QVBoxLayout(self)
 layout.setContentsMargins(20, 20, 20, 20)
 layout.setSpacing(15)
 
 # Now playing section
 now_playing_frame = QFrame()
 now_playing_layout = QVBoxLayout(now_playing_frame)
 now_playing_layout.setContentsMargins(15, 15, 15, 15)
 now_playing_layout.setSpacing(10)
 
 # Title
 self._title_label = QLabel("No audiobook selected")
 self._title_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
 self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
 self._title_label.setWordWrap(True)
 
 # Author
 self._author_label = QLabel("")
 self._author_label.setFont(QFont("Segoe UI", 14))
 self._author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
 self._author_label.setStyleSheet("color: #888888;")
 
 # Chapter info
 self._chapter_label = QLabel("")
 self._chapter_label.setFont(QFont("Segoe UI", 12))
 self._chapter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
 self._chapter_label.setStyleSheet("color: #666666;")
 
 now_playing_layout.addWidget(self._title_label)
 now_playing_layout.addWidget(self._author_label)
 now_playing_layout.addWidget(self._chapter_label)
 
 # Cover art
 self._cover_label = QLabel()
 self._cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
 self._cover_label.setFixedSize(200, 200)
 self._cover_label.setStyleSheet(
 "background-color: #1a1a2e; border-radius: 10px;"
 )
 
 # Progress section
 progress_frame = QFrame()
 progress_layout = QVBoxLayout(progress_frame)
 progress_layout.setContentsMargins(10, 10, 10, 10)
 progress_layout.setSpacing(5)
 
 # Progress slider
 self._progress_slider = QSlider(Qt.Orientation.Horizontal)
 self._progress_slider.setRange(0, 1000) # 0-1000 for precision
 self._progress_slider.setValue(0)
 self._progress_slider.setStyleSheet("""
 QSlider::groove:horizontal {
 background-color: #0f3460;
 height: 6px;
 border-radius: 3px;
 }
 QSlider::handle:horizontal {
 background-color: #e94560;
 width: 16px;
 height: 16px;
 border-radius: 8px;
 margin: -5px 0;
 }
 QSlider::add-page:horizontal {
 background-color: #1a4a7a;
 border-radius: 3px;
 }
 QSlider::sub-page:horizontal {
 background-color: #e94560;
 border-radius: 3px;
 }
 """)
 
 # Time labels
 time_layout = QHBoxLayout()
 self._current_time_label = QLabel("00:00")
 self._current_time_label.setFont(QFont("Segoe UI", 12))
 self._current_time_label.setStyleSheet("color: #888888;")
 
 self._duration_label = QLabel("00:00")
 self._duration_label.setFont(QFont("Segoe UI", 12))
 self._duration_label.setStyleSheet("color: #888888;")
 
 time_layout.addWidget(self._current_time_label)
 time_layout.addStretch()
 time_layout.addWidget(self._duration_label)
 
 progress_layout.addWidget(self._progress_slider)
 progress_layout.addLayout(time_layout)
 
 # Controls section
 controls_frame = QFrame()
 controls_layout = QHBoxLayout(controls_frame)
 controls_layout.setContentsMargins(15, 15, 15, 15)
 controls_layout.setSpacing(20)
 
 # Control buttons
 self._previous_button = QToolButton()
 self._previous_button.setIcon(self._create_icon("⏮"))
 self._previous_button.setToolTip("Previous Chapter")
 self._previous_button.setFixedSize(48, 48)
 self._previous_button.setStyleSheet("""
 QToolButton {
 background-color: #0f3460;
 border-radius: 24px;
 font-size: 20px;
 }
 QToolButton:hover {
 background-color: #1a4a7a;
 }
 QToolButton:pressed {
 background-color: #e94560;
 }
 """)
 
 self._seek_backward_30_button = QToolButton()
 self._seek_backward_30_button.setIcon(self._create_icon("⏪ 30"))
 self._seek_backward_30_button.setToolTip("Seek Backward 30s")
 self._seek_backward_30_button.setFixedSize(48, 48)
 self._seek_backward_30_button.setStyleSheet("""
 QToolButton {
 background-color: #0f3460;
 border-radius: 24px;
 font-size: 14px;
 }
 QToolButton:hover {
 background-color: #1a4a7a;
 }
 QToolButton:pressed {
 background-color: #e94560;
 }
 """)
 
 self._seek_backward_10_button = QToolButton()
 self._seek_backward_10_button.setIcon(self._create_icon("⏪ 10"))
 self._seek_backward_10_button.setToolTip("Seek Backward 10s")
 self._seek_backward_10_button.setFixedSize(48, 48)
 self._seek_backward_10_button.setStyleSheet("""
 QToolButton {
 background-color: #0f3460;
 border-radius: 24px;
 font-size: 14px;
 }
 QToolButton:hover {
 background-color: #1a4a7a;
 }
 QToolButton:pressed {
 background-color: #e94560;
 }
 """)
 
 self._play_pause_button = QToolButton()
 self._play_pause_button.setIcon(self._create_icon("▶"))
 self._play_pause_button.setToolTip("Play/Pause")
 self._play_pause_button.setFixedSize(64, 64)
 self._play_pause_button.setStyleSheet("""
 QToolButton {
 background-color: #e94560;
 border-radius: 32px;
 font-size: 24px;
 }
 QToolButton:hover {
 background-color: #c73652;
 }
 QToolButton:pressed {
 background-color: #a52840;
 }
 """)
 
 self._seek_forward_10_button = QToolButton()
 self._seek_forward_10_button.setIcon(self._create_icon("⏩ 10"))
 self._seek_forward_10_button.setToolTip("Seek Forward 10s")
 self._seek_forward_10_button.setFixedSize(48, 48)
 self._seek_forward_10_button.setStyleSheet("""
 QToolButton {
 background-color: #0f3460;
 border-radius: 24px;
 font-size: 14px;
 }
 QToolButton:hover {
 background-color: #1a4a7a;
 }
 QToolButton:pressed {
 background-color: #e94560;
 }
 """)
 
 self._seek_forward_30_button = QToolButton()
 self._seek_forward_30_button.setIcon(self._create_icon("⏩ 30"))
 self._seek_forward_30_button.setToolTip("Seek Forward 30s")
 self._seek_forward_30_button.setFixedSize(48, 48)
 self._seek_forward_30_button.setStyleSheet("""
 QToolButton {
 background-color: #0f3460;
 border-radius: 24px;
 font-size: 14px;
 }
 QToolButton:hover {
 background-color: #1a4a7a;
 }
 QToolButton:pressed {
 background-color: #e94560;
 }
 """)
 
 self._next_button = QToolButton()
 self._next_button.setIcon(self._create_icon("⏭"))
 self._next_button.setToolTip("Next Chapter")
 self._next_button.setFixedSize(48, 48)
 self._next_button.setStyleSheet("""
 QToolButton {
 background-color: #0f3460;
 border-radius: 24px;
 font-size: 20px;
 }
 QToolButton:hover {
 background-color: #1a4a7a;
 }
 QToolButton:pressed {
 background-color: #e94560;
 }
 """)
 
 controls_layout.addWidget(self._previous_button)
 controls_layout.addWidget(self._seek_backward_30_button)
 controls_layout.addWidget(self._seek_backward_10_button)
 controls_layout.addWidget(self._play_pause_button)
 controls_layout.addWidget(self._seek_forward_10_button)
 controls_layout.addWidget(self._seek_forward_30_button)
 controls_layout.addWidget(self._next_button)
 
 # Additional controls (volume, speed)
 additional_controls = QHBoxLayout()
 additional_controls.setSpacing(15)
 
 # Volume control
 volume_layout = QHBoxLayout()
 volume_layout.setSpacing(5)
 
 volume_icon = QLabel("🔊")
 volume_icon.setFont(QFont("Segoe UI", 14))
 
 self._volume_slider = QSlider(Qt.Orientation.Horizontal)
 self._volume_slider.setRange(0, 100)
 self._volume_slider.setValue(int(player.get_volume() * 100))
 self._volume_slider.setFixedWidth(100)
 self._volume_slider.setStyleSheet("""
 QSlider::groove:horizontal {
 background-color: #0f3460;
 height: 4px;
 border-radius: 2px;
 }
 QSlider::handle:horizontal {
 background-color: #e94560;
 width: 12px;
 height: 12px;
 border-radius: 6px;
 margin: -4px 0;
 }
 """)
 
 volume_layout.addWidget(volume_icon)
 volume_layout.addWidget(self._volume_slider)
 
 # Speed control
 speed_layout = QHBoxLayout()
 speed_layout.setSpacing(5)
 
 speed_icon = QLabel("⚡")
 speed_icon.setFont(QFont("Segoe UI", 14))
 
 self._speed_combo = self._create_speed_combo()
 
 speed_layout.addWidget(speed_icon)
 speed_layout.addWidget(self._speed_combo)
 
 additional_controls.addLayout(volume_layout)
 additional_controls.addStretch()
 additional_controls.addLayout(speed_layout)
 
 # Assemble main layout
 layout.addWidget(now_playing_frame)
 layout.addWidget(self._cover_label, alignment=Qt.AlignmentFlag.AlignCenter)
 layout.addWidget(progress_frame)
 layout.addWidget(controls_frame)
 layout.addLayout(additional_controls)
 
 # Set initial state
 self._update_play_pause_icon()
 
 def _create_icon(self, text: str) -> QIcon:
 """Create an icon from text"""
 # For simplicity, we'll use text as icon
 # In production, use proper icons
 pixmap = QPixmap(48, 48)
 pixmap.fill(Qt.GlobalColor.transparent)
 return QIcon(pixmap)
 
 def _create_speed_combo(self):
 """Create speed selection combo box"""
 from PyQt6.QtWidgets import QComboBox
 combo = QComboBox()
 combo.setFixedWidth(80)
 combo.addItems(["0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x"])
 
 # Set current speed
 current_speed = player.get_speed()
 index = combo.findText(f"{current_speed}x")
 if index >= 0:
 combo.setCurrentIndex(index)
 else:
 combo.setCurrentIndex(2) # Default to 1.0x
 
 combo.setStyleSheet("""
 QComboBox {
 background-color: #0f3460;
 color: #eaeaea;
 border: 1px solid #1a4a7a;
 border-radius: 6px;
 padding: 5px 10px;
 }
 QComboBox::drop-down {
 border: none;
 }
 QComboBox QAbstractItemView {
 background-color: #0f3460;
 color: #eaeaea;
 selection-background-color: #e94560;
 }
 """)
 
 return combo
 
 def _setup_connections(self):
 """Setup signal connections"""
 self._play_pause_button.clicked.connect(self._on_play_pause_clicked)
 self._previous_button.clicked.connect(self._on_previous_clicked)
 self._next_button.clicked.connect(self._on_next_clicked)
 self._seek_backward_10_button.clicked.connect(lambda: self.seek_backward_clicked.emit(10))
 self._seek_backward_30_button.clicked.connect(lambda: self.seek_backward_clicked.emit(30))
 self._seek_forward_10_button.clicked.connect(lambda: self.seek_forward_clicked.emit(10))
 self._seek_forward_30_button.clicked.connect(lambda: self.seek_forward_clicked.emit(30))
 
 self._volume_slider.valueChanged.connect(self._on_volume_changed)
 self._speed_combo.currentTextChanged.connect(self._on_speed_changed)
 self._progress_slider.sliderMoved.connect(self._on_progress_slider_moved)
 
 # Player callbacks
 player.on_playback_start = self._on_player_playback_start
 player.on_playback_pause = self._on_player_playback_pause
 player.on_playback_resume = self._on_player_playback_resume
 player.on_playback_stop = self._on_player_playback_stop
 player.on_position_change = self._on_player_position_change
 
 def _update_playback_info(self):
 """Update playback information"""
 if self._updating_slider:
 return
 
 # Update position
 position = player.get_current_position()
 duration = player.get_current_duration()
 
 self._current_time_label.setText(format_duration(position))
 self._duration_label.setText(format_duration(duration))
 
 if duration > 0:
 progress = (position / duration) * 1000
 self._progress_slider.setValue(int(progress))
 
 def _update_play_pause_icon(self):
 """Update play/pause button icon"""
 if player.is_playing():
 self._play_pause_button.setIcon(self._create_icon("⏸"))
 self._play_pause_button.setToolTip("Pause")
 else:
 self._play_pause_button.setIcon(self._create_icon("▶"))
 self._play_pause_button.setToolTip("Play")
 
 def set_audiobook(self, audiobook: Optional[Audiobook], chapter: Optional[dict]):
 """Set the current audiobook and chapter"""
 self._audiobook = audiobook
 self._chapter = chapter
 
 if audiobook:
 self._title_label.setText(audiobook.title)
 self._author_label.setText(audiobook.author)
 
 if chapter:
 self._chapter_label.setText(f"Chapter {chapter.get('index', 0) + 1}: {chapter.get('title', 'Unknown')}")
 else:
 self._chapter_label.setText("")
 
 # Try to load cover
 self._load_cover(audiobook)
 else:
 self._title_label.setText("No audiobook selected")
 self._author_label.setText("")
 self._chapter_label.setText("")
 self._cover_label.clear()
 
 def _load_cover(self, audiobook: Audiobook):
 """Load cover image for audiobook"""
 # For now, just show a placeholder
 # In production, download and cache the cover
 if audiobook.cover:
 # Download cover in background
 pass
 
 # Show placeholder
 self._cover_label.setText("📖")
 self._cover_label.setFont(QFont("Segoe UI", 64))
 
 # Event handlers
 def _on_play_pause_clicked(self):
 """Handle play/pause button click"""
 self.play_pause_clicked.emit()
 self._update_play_pause_icon()
 
 def _on_previous_clicked(self):
 """Handle previous button click"""
 self.previous_clicked.emit()
 
 def _on_next_clicked(self):
 """Handle next button click"""
 self.next_clicked.emit()
 
 def _on_volume_changed(self, value: int):
 """Handle volume slider change"""
 volume = value / 100.0
 self.volume_changed.emit(volume)
 
 def _on_speed_changed(self, text: str):
 """Handle speed combo change"""
 try:
 speed = float(text.replace("x", ""))
 self.speed_changed.emit(speed)
 except ValueError:
 pass
 
 def _on_progress_slider_moved(self, value: int):
 """Handle progress slider move"""
 duration = player.get_current_duration()
 if duration > 0:
 position = (value / 1000) * duration
 player.seek(position)
 
 # Player callbacks
 def _on_player_playback_start(self):
 """Handle player playback start"""
 self._update_play_pause_icon()
 
 def _on_player_playback_pause(self):
 """Handle player playback pause"""
 self._update_play_pause_icon()
 
 def _on_player_playback_resume(self):
 """Handle player playback resume"""
 self._update_play_pause_icon()
 
 def _on_player_playback_stop(self):
 """Handle player playback stop"""
 self._update_play_pause_icon()
 self.set_audiobook(None, None)
 
 def _on_player_position_change(self, position: float):
 """Handle player position change"""
 self._update_playback_info()
 
 def cleanup(self):
 """Cleanup resources"""
 self._update_timer.stop()
