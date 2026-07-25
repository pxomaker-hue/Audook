"""
Main application window
Contains sidebar, pages, and player
"""

from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QPushButton, QLabel, QStackedWidget)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from app.ui.styles import MAIN_STYLESHEET
from app.ui.pages import HomePage, ExplorePage
from app.ui.widgets import PlayerWidget
from app.player import player
from app.utils import logger
from app.services import LibraryService, player_service, sync_service


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audook - Audiobook Player")
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet(MAIN_STYLESHEET)

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """Initialize main UI"""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Content area with sidebar
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Sidebar
        self.sidebar = self._create_sidebar()
        content_layout.addWidget(self.sidebar)

        # Pages (stacked widget)
        self.pages = QStackedWidget()
        self.home_page = HomePage()
        self.explore_page = ExplorePage()

        self.pages.addWidget(self.home_page)
        self.pages.addWidget(self.explore_page)

        content_layout.addWidget(self.pages)

        main_layout.addLayout(content_layout)

        # Player widget at bottom
        self.player_widget = PlayerWidget()
        main_layout.addWidget(self.player_widget)

    def _create_sidebar(self) -> QWidget:
        """Create sidebar navigation"""
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(200)
        sidebar.setMaximumWidth(200)
        sidebar.setStyleSheet("""
            QWidget#sidebar {
                background-color: #ffffff;
                border-right: 1px solid #e0e0e0;
            }
        """)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 24, 0, 24)
        layout.setSpacing(8)

        # App logo/title
        app_title = QLabel("Audook")
        app_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        app_title.setFont(title_font)
        app_title.setStyleSheet("color: #000000; margin-bottom: 24px;")
        layout.addWidget(app_title)

        # Navigation buttons
        self.nav_buttons = {}

        nav_items = [
            ("library", "📚 My Library", 0),
            ("explore", "🔍 Explore", 1),
            ("history", "📖 History", -1),
            ("settings", "⚙️ Settings", -1),
        ]

        for key, label, page_idx in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("sidebar_btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(44)
            btn.setMaximumHeight(44)

            if page_idx >= 0:
                btn.clicked.connect(lambda checked, idx=page_idx: self.show_page(idx))
            else:
                btn.clicked.connect(lambda checked, name=key: logger.info(f"Clicked {name}"))

            layout.addWidget(btn)
            self.nav_buttons[key] = btn

        # Set library as active
        self.nav_buttons["library"].setProperty("class", "active")

        layout.addStretch()

        return sidebar

    def show_page(self, index: int):
        """Show a page by index"""
        self.pages.setCurrentIndex(index)

        # Update active button
        for btn in self.nav_buttons.values():
            btn.setProperty("class", "")

        if index == 0:
            self.nav_buttons["library"].setProperty("class", "active")
        elif index == 1:
            self.nav_buttons["explore"].setProperty("class", "active")

        # Trigger style update
        self.style().unpolish(self.sidebar)
        self.style().polish(self.sidebar)

    def connect_signals(self):
        """Connect signals from pages to handlers"""
        self.home_page.book_selected.connect(self.on_book_selected)
        self.home_page.sync_requested.connect(self.on_sync_requested)
        self.explore_page.book_selected.connect(self.on_book_selected)

        # Connect player signals
        self.player_widget.play_pause.connect(self.on_play_pause)
        self.player_widget.next_track.connect(self.on_next_track)
        self.player_widget.prev_track.connect(self.on_prev_track)
        self.player_widget.seek.connect(self.on_seek)
        self.player_widget.volume_changed.connect(self.on_volume_changed)

        # Connect sync progress
        sync_service.on_sync_progress(self.on_sync_progress)

        # Connect player service position updates
        player_service.on_position_changed(self.on_player_position_changed)

    def on_book_selected(self, book_id: str):
        """Handle book selection"""
        logger.info(f"Book selected: {book_id}")

        # Load book from database
        audiobook = LibraryService.get_book_by_id(book_id)
        if not audiobook:
            logger.error(f"Book not found: {book_id}")
            return

        # Start playback
        if player_service.start_playbook(audiobook):
            self.player_widget.set_now_playing(audiobook.title, audiobook.author or "Unknown")
            self.player_widget.is_playing = True
            self.player_widget.update_play_button()
            logger.info(f"Now playing: {audiobook.title}")
        else:
            logger.error(f"Failed to start playback: {book_id}")

    def on_play_pause(self):
        """Handle play/pause"""
        if self.player_widget.is_playing:
            player_service.pause()
        else:
            player_service.resume()

    def on_next_track(self):
        """Handle next track"""
        player_service.next_chapter()

    def on_prev_track(self):
        """Handle previous track"""
        player_service.previous_chapter()

    def on_seek(self, position: int):
        """Handle seek"""
        player_service.seek(position)

    def on_volume_changed(self, volume: int):
        """Handle volume change"""
        player_service.set_volume(volume)

    def on_sync_requested(self):
        """Handle sync button click"""
        logger.info("Sync requested")
        sync_service.sync_all_servers(background=True)

    def on_sync_progress(self, message: str, is_complete: bool):
        """Handle sync progress updates"""
        logger.info(f"Sync: {message}")
        if is_complete:
            # Reload books in UI
            self.home_page.load_books()

    def on_player_position_changed(self, position: float, duration: float):
        """Handle player position updates"""
        # Update player widget
        self.player_widget.update_progress(int(position * 1000), int(duration * 1000))

    def closeEvent(self, event):
        """Handle window close"""
        player.shutdown()
        event.accept()
