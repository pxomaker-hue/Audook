"""
Main window for Audook
The primary application window
"""

import asyncio
from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QStackedWidget, QPushButton, QToolButton, QLabel, QFrame
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon, QFont

from app.models import Audiobook, Library, ServerConfig
from app.player.player import player
from app.player.queue import queue
from app.utils.config_manager import config_manager
from app.ui.library_view import LibraryView
from app.ui.player_view import PlayerView
from app.ui.settings_view import SettingsView
from app.ui import apply_theme, get_stylesheet
from app.audiobookshelf.client import AudiobookshelfClient
from app.plex.client import PlexClient


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self._current_client: Optional[Any] = None
        self._current_server: Optional[ServerConfig] = None
        self._current_library: Optional[Library] = None
        self._audiobooks: List[Audiobook] = []
        self._is_loading = False

        self._init_ui()
        self._setup_connections()
        self._load_initial_data()

    def _init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("Audook")
        self.setMinimumSize(1000, 700)

        # Set window icon (placeholder)
        self.setWindowIcon(QIcon())

        # Apply theme
        apply_theme(self, config_manager.config.theme)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        self._header = self._create_header()
        main_layout.addWidget(self._header)

        # Main content
        self._main_content = QSplitter(Qt.Orientation.Vertical)
        self._main_content.setHandleWidth(8)
        self._main_content.setStyleSheet("""
            QSplitter::handle:vertical {
                background-color: #1a4a7a;
                border-radius: 4px;
            }
        """)

        # Library view
        self._library_view = LibraryView()

        # Player view
        self._player_view = PlayerView()

        # Add to splitter
        self._main_content.addWidget(self._library_view)
        self._main_content.addWidget(self._player_view)

        # Set initial sizes
        self._main_content.setSizes([400, 200])

        main_layout.addWidget(self._main_content)

        # Status bar
        self._status_bar = QLabel("Prêt")
        self._status_bar.setFont(QFont("Segoe UI", 12))
        self._status_bar.setStyleSheet("color: #888888; padding: 10px;")
        main_layout.addWidget(self._status_bar)

        # Settings dialog (hidden by default)
        self._settings_dialog = SettingsView()
        self._settings_dialog.setWindowTitle("Paramètres")
        self._settings_dialog.setMinimumSize(600, 500)

    def _create_header(self) -> QWidget:
        """Create header widget"""
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet("""
            QFrame {
                background-color: #0f3460;
                border-bottom: 1px solid #1a4a7a;
            }
        """)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(10)

        # Logo
        logo = QLabel("📚 Audook")
        logo.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        logo.setStyleSheet("color: #e94560;")

        # Navigation buttons
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(5)

        self._library_button = QToolButton()
        self._library_button.setText("📚 Bibliothèque")
        self._library_button.setFont(QFont("Segoe UI", 14))
        self._library_button.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                color: #eaeaea;
                border: none;
                padding: 8px 16px;
            }
            QToolButton:hover {
                background-color: #1a4a7a;
                border-radius: 6px;
            }
        """)
        self._library_button.setCheckable(True)
        self._library_button.setChecked(True)

        self._queue_button = QToolButton()
        self._queue_button.setText("🎵 File d'attente")
        self._queue_button.setFont(QFont("Segoe UI", 14))
        self._queue_button.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                color: #eaeaea;
                border: none;
                padding: 8px 16px;
            }
            QToolButton:hover {
                background-color: #1a4a7a;
                border-radius: 6px;
            }
        """)
        self._queue_button.setCheckable(True)

        self._bookmarks_button = QToolButton()
        self._bookmarks_button.setText("🔖 Marque-pages")
        self._bookmarks_button.setFont(QFont("Segoe UI", 14))
        self._bookmarks_button.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                color: #eaeaea;
                border: none;
                padding: 8px 16px;
            }
            QToolButton:hover {
                background-color: #1a4a7a;
                border-radius: 6px;
            }
        """)
        self._bookmarks_button.setCheckable(True)

        nav_layout.addWidget(self._library_button)
        nav_layout.addWidget(self._queue_button)
        nav_layout.addWidget(self._bookmarks_button)

        # Settings button
        self._settings_button = QToolButton()
        self._settings_button.setText("⚙️")
        self._settings_button.setFont(QFont("Segoe UI", 16))
        self._settings_button.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                color: #eaeaea;
                border: none;
                padding: 8px 16px;
            }
            QToolButton:hover {
                background-color: #1a4a7a;
                border-radius: 6px;
            }
        """)

        layout.addWidget(logo)
        layout.addStretch()
        layout.addLayout(nav_layout)
        layout.addWidget(self._settings_button)

        return header

    def _setup_connections(self):
        """Setup signal connections"""
        # Library view signals
        self._library_view.audiobook_selected.connect(self._on_audiobook_selected)
        self._library_view.audiobook_double_clicked.connect(self._on_audiobook_double_clicked)
        self._library_view.library_changed.connect(self._on_library_changed)
        self._library_view.server_changed.connect(self._on_server_changed)
        self._library_view.refresh_requested.connect(self._on_refresh_requested)
        self._library_view.search_requested.connect(self._on_search_requested)
        self._library_view.download_requested.connect(self._on_download_requested)

        # Player view signals
        self._player_view.play_pause_clicked.connect(self._on_play_pause_clicked)
        self._player_view.previous_clicked.connect(self._on_previous_clicked)
        self._player_view.next_clicked.connect(self._on_next_clicked)
        self._player_view.seek_backward_clicked.connect(self._on_seek_backward)
        self._player_view.seek_forward_clicked.connect(self._on_seek_forward)
        self._player_view.volume_changed.connect(self._on_volume_changed)
        self._player_view.speed_changed.connect(self._on_speed_changed)

        # Header buttons
        self._settings_button.clicked.connect(self._on_settings_clicked)

        # Player callbacks (already set in PlayerView)

        # Settings dialog signals
        self._settings_dialog._server_settings.server_added.connect(self._on_server_added)
        self._settings_dialog._server_settings.server_updated.connect(self._on_server_updated)
        self._settings_dialog._server_settings.server_removed.connect(self._on_server_removed)

    def _load_initial_data(self):
        """Load initial data"""
        # Load servers
        servers = config_manager.config.servers
        self._library_view.set_servers(servers)

        # Set current server
        if config_manager.config.current_server_id:
            self._library_view.set_current_server(config_manager.config.current_server_id)
            self._on_server_changed(config_manager.config.current_server_id)
        elif servers:
            self._library_view.set_current_server(servers[0].id)
            self._on_server_changed(servers[0].id)

    async def _load_libraries(self, server: ServerConfig):
        """Load libraries from server"""
        self._is_loading = True
        self._status_bar.setText("Chargement des bibliothèques...")

        try:
            if server.type == "audiobookshelf":
                client = AudiobookshelfClient(server.url, server.api_key or "")
            else:
                client = PlexClient(server.url, server.api_key or server.password or "")

            libraries = await client.get_libraries()

            # Update UI
            self._library_view.set_libraries(libraries)

            if libraries:
                # Set first library as current
                self._library_view.set_current_library(libraries[0].id)
                self._current_library = libraries[0]

                # Load audiobooks
                await self._load_audiobooks(libraries[0])

            self._status_bar.setText(f"Connecté à {server.name}")

        except Exception as e:
            self._status_bar.setText(f"Erreur: {str(e)}")
        finally:
            self._is_loading = False

    async def _load_audiobooks(self, library: Library):
        """Load audiobooks from library"""
        if not self._current_server:
            return

        self._is_loading = True
        self._status_bar.setText(f"Chargement des audiobooks de {library.name}...")

        try:
            if self._current_server.type == "audiobookshelf":
                client = AudiobookshelfClient(self._current_server.url, self._current_server.api_key or "")
            else:
                client = PlexClient(self._current_server.url, self._current_server.api_key or self._current_server.password or "")

            audiobooks = await client.get_audiobooks(library.id, limit=100)

            # Update UI
            self._audiobooks = audiobooks
            self._library_view.set_audiobooks(audiobooks)

            self._status_bar.setText(f"{len(audiobooks)} audiobooks chargés")

        except Exception as e:
            self._status_bar.setText(f"Erreur: {str(e)}")
        finally:
            self._is_loading = False

    # Event handlers
    def _on_server_changed(self, server_id: str):
        """Handle server change"""
        server = config_manager.get_server_by_id(server_id)
        if not server:
            return

        self._current_server = server
        config_manager.config.current_server_id = server_id
        config_manager.save_config()

        # Load libraries
        asyncio.create_task(self._load_libraries(server))

    def _on_library_changed(self, library_id: str):
        """Handle library change"""
        for lib in self._library_view._libraries:
            if lib.id == library_id:
                self._current_library = lib
                config_manager.config.current_library_id = library_id
                config_manager.save_config()

                # Load audiobooks
                asyncio.create_task(self._load_audiobooks(lib))
                break

    def _on_audiobook_selected(self, audiobook: Audiobook, chapter: dict):
        """Handle audiobook selection"""
        self._player_view.set_audiobook(audiobook, chapter)

        # Add to queue
        queue.clear()
        for chap in audiobook.chapters:
            queue.add(audiobook, chap)

        # Set current in queue
        queue.set_current(0)

    def _on_audiobook_double_clicked(self, audiobook: Audiobook):
        """Handle audiobook double click"""
        if audiobook.chapters:
            chapter = audiobook.chapters[0]
            self._on_audiobook_selected(audiobook, chapter)
            self._on_play_pause_clicked()

    def _on_play_pause_clicked(self):
        """Handle play/pause click"""
        if player.is_playing():
            player.pause()
        else:
            # Get current from queue
            current = queue.get_current()
            if current:
                audiobook = current["audiobook"]
                chapter = current["chapter"]
                player.play(audiobook, chapter)
            else:
                # Try to play from library selection
                if self._player_view.get_current_audiobook():
                    audiobook = self._player_view.get_current_audiobook()
                    chapter = self._player_view.get_current_chapter()
                    if audiobook and chapter:
                        player.play(audiobook, chapter)

    def _on_previous_clicked(self):
        """Handle previous chapter click"""
        player.previous_chapter()

    def _on_next_clicked(self):
        """Handle next chapter click"""
        player.next_chapter()

    def _on_seek_backward(self, seconds: int):
        """Handle seek backward"""
        player.seek_relative(-seconds)

    def _on_seek_forward(self, seconds: int):
        """Handle seek forward"""
        player.seek_relative(seconds)

    def _on_volume_changed(self, volume: float):
        """Handle volume change"""
        player.set_volume(volume)

    def _on_speed_changed(self, speed: float):
        """Handle speed change"""
        player.set_speed(speed)

    def _on_refresh_requested(self):
        """Handle refresh request"""
        if self._current_library:
            asyncio.create_task(self._load_audiobooks(self._current_library))

    def _on_search_requested(self, query: str):
        """Handle search request"""
        if not query or not self._current_server or not self._current_library:
            return

        asyncio.create_task(self._search_audiobooks(query))

    async def _search_audiobooks(self, query: str):
        """Search audiobooks"""
        self._is_loading = True
        self._status_bar.setText(f"Recherche de '{query}'...")

        try:
            if self._current_server.type == "audiobookshelf":
                client = AudiobookshelfClient(self._current_server.url, self._current_server.api_key or "")
            else:
                client = PlexClient(self._current_server.url, self._current_server.api_key or self._current_server.password or "")

            audiobooks = await client.search(self._current_library.id, query, limit=20)

            # Update UI
            self._audiobooks = audiobooks
            self._library_view.set_audiobooks(audiobooks)

            self._status_bar.setText(f"{len(audiobooks)} résultats trouvés")

        except Exception as e:
            self._status_bar.setText(f"Erreur: {str(e)}")
        finally:
            self._is_loading = False

    def _on_download_requested(self, audiobook: Audiobook):
        """Handle download request"""
        self._status_bar.setText(f"Téléchargement de {audiobook.title}...")

        # TODO: Implement download
        # For now, just show message
        self._status_bar.setText(f"Téléchargement démarré: {audiobook.title}")

    def _on_settings_clicked(self):
        """Handle settings button click"""
        self._settings_dialog.show()

    def _on_server_added(self, server: ServerConfig):
        """Handle server added"""
        self._load_initial_data()

    def _on_server_updated(self, server: ServerConfig):
        """Handle server updated"""
        self._load_initial_data()

    def _on_server_removed(self, server_id: str):
        """Handle server removed"""
        if self._current_server and self._current_server.id == server_id:
            self._current_server = None
            self._library_view.set_libraries([])
            self._library_view.set_audiobooks([])

        self._load_initial_data()

    def closeEvent(self, event):
        """Handle close event"""
        # Save playback state
        if player.is_playing() or player.is_paused():
            config_manager.save_playback_state()

        # Cleanup
        player.cleanup()

        event.accept()
