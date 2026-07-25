"""
Main window for Audook - Complete application window
"""

import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QFrame, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from app.models import Audiobook, Library, ServerConfig
from app.player.player import player
from app.player.queue import queue
from app.utils.config_manager import config_manager
from app.utils import logger
from app.ui.library_view import LibraryView
from app.ui.player_view import PlayerView
from app.ui.settings_view import SettingsView
from app.ui import apply_theme
from app.audiobookshelf.client import AudiobookshelfClient
from app.plex.client import PlexClient
from app.local.client import LocalClient


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self._current_client: Optional[Any] = None
        self._current_server: Optional[ServerConfig] = None
        self._current_library: Optional[Library] = None
        self._audiobooks: List[Audiobook] = []
        self._is_loading: bool = False

        self._init_ui()
        self._setup_connections()
        self._setup_player_callbacks()
        self._load_initial_data()

    def _init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("Audook - Audiobook Player")
        self.setMinimumSize(1200, 800)

        # Apply theme
        apply_theme(self, config_manager.config.theme)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Content area
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Library view
        self._library_view = LibraryView()
        content_layout.addWidget(self._library_view, stretch=1)

        # Player view
        self._player_view = PlayerView()
        content_layout.addWidget(self._player_view, stretch=0)

        main_layout.addLayout(content_layout)

        # Status bar
        self._status_bar = QLabel("Prêt")
        self._status_bar.setFont(QFont("Segoe UI", 10))
        self._status_bar.setStyleSheet("""
            QLabel {
                background-color: #0d1117;
                color: #888888;
                padding: 8px 16px;
                border-top: 1px solid #2a3f5f;
            }
        """)
        main_layout.addWidget(self._status_bar)

        # Settings dialog
        self._settings_dialog = SettingsView()
        self._settings_dialog.setWindowTitle("Paramètres")
        self._settings_dialog.setMinimumSize(600, 500)

    def _setup_connections(self):
        """Setup signal connections"""
        # Library view signals
        self._library_view.audiobook_selected.connect(self._on_audiobook_selected)
        self._library_view.audiobook_double_clicked.connect(self._on_audiobook_double_clicked)
        self._library_view.library_changed.connect(self._on_library_changed)
        self._library_view.server_changed.connect(self._on_server_changed)
        self._library_view.refresh_requested.connect(self._on_refresh_requested)
        self._library_view.search_requested.connect(self._on_search_requested)

        # Player view signals
        self._player_view.play_pause_clicked.connect(self._on_play_pause_clicked)
        self._player_view.previous_clicked.connect(self._on_previous_clicked)
        self._player_view.next_clicked.connect(self._on_next_clicked)
        self._player_view.seek_backward_clicked.connect(self._on_seek_backward)
        self._player_view.seek_forward_clicked.connect(self._on_seek_forward)
        self._player_view.volume_changed.connect(self._on_volume_changed)
        self._player_view.speed_changed.connect(self._on_speed_changed)

    def _setup_player_callbacks(self):
        """Setup player callbacks"""
        player.set_on_playback_start(lambda: self._player_view.set_playing(True))
        player.set_on_playback_pause(lambda: self._player_view.set_playing(False))
        player.set_on_playback_resume(lambda: self._player_view.set_playing(True))
        player.set_on_playback_stop(lambda: self._player_view.set_playing(False))
        player.set_on_position_change(lambda pos: self._player_view.set_position(pos))

    def _load_initial_data(self):
        """Load initial data"""
        # Load servers
        servers = config_manager.config.servers
        self._library_view.set_servers(servers)

        # Load last used server if available
        if config_manager.config.current_server_id:
            self._library_view.set_current_server(config_manager.config.current_server_id)

    # Event handlers - Server/Library Selection

    def _on_server_changed(self, server_id: str):
        """Handle server change"""
        logger.info(f"Server changed: {server_id}")

        if server_id == "local":
            # Open directory picker for local library
            folder = QFileDialog.getExistingDirectory(
                self,
                "Sélectionner un dossier avec des audiobooks",
                str(Path.home() / "Music")
            )
            if folder:
                asyncio.create_task(self._load_local_library(folder))
            return

        # Load remote server
        server = config_manager.get_server_by_id(server_id)
        if not server:
            self._status_bar.setText("Serveur non trouvé")
            return

        self._current_server = server
        config_manager.config.current_server_id = server_id
        config_manager.save_config()

        asyncio.create_task(self._load_libraries(server))

    def _on_library_changed(self, library_id: str):
        """Handle library change"""
        logger.info(f"Library changed: {library_id}")

        for lib in self._library_view._libraries:
            if lib.id == library_id:
                self._current_library = lib
                config_manager.config.current_library_id = library_id
                config_manager.save_config()

                if self._current_client:
                    asyncio.create_task(self._load_audiobooks(self._current_client, lib))
                break

    def _on_refresh_requested(self):
        """Handle refresh request"""
        if self._current_library and self._current_client:
            asyncio.create_task(self._load_audiobooks(self._current_client, self._current_library))

    def _on_search_requested(self, query: str):
        """Handle search request"""
        # Filter audiobooks based on search query
        if query.strip() == "":
            self._library_view.set_audiobooks(self._audiobooks)
        else:
            filtered = [
                ab for ab in self._audiobooks
                if query.lower() in ab.title.lower() or query.lower() in ab.author.lower()
            ]
            self._library_view.set_audiobooks(filtered)

    # Event handlers - Library Loading

    async def _load_libraries(self, server: ServerConfig):
        """Load libraries from server"""
        self._is_loading = True
        self._status_bar.setText(f"Chargement des bibliothèques de {server.name}...")

        try:
            if server.type == "audiobookshelf":
                self._current_client = AudiobookshelfClient(server.url, server.api_key or "")
            elif server.type == "plex":
                self._current_client = PlexClient(server.url, server.api_key or server.password or "")
            else:
                raise ValueError(f"Unknown server type: {server.type}")

            libraries = await self._current_client.get_libraries()

            if not libraries:
                self._status_bar.setText(f"Aucune bibliothèque trouvée")
                return

            self._library_view.set_libraries(libraries)

            if libraries:
                self._current_library = libraries[0]
                self._library_view.set_current_library(libraries[0].id)
                await self._load_audiobooks(self._current_client, libraries[0])

            self._status_bar.setText(f"Connecté à {server.name}")

        except Exception as e:
            logger.error(f"Failed to load libraries: {e}")
            self._status_bar.setText(f"Erreur: {str(e)}")
        finally:
            self._is_loading = False

    async def _load_local_library(self, folder_path: str):
        """Load audiobooks from a local folder"""
        self._is_loading = True
        folder_name = Path(folder_path).name
        self._status_bar.setText(f"Lecture du dossier {folder_name}...")

        try:
            self._current_client = LocalClient(folder_path)

            if not await self._current_client.ping():
                self._status_bar.setText("Erreur: Le dossier n'est pas accessible")
                return

            libraries = await self._current_client.get_libraries()

            if not libraries:
                self._status_bar.setText("Erreur: Impossible de lire le dossier")
                return

            self._library_view.set_libraries(libraries)
            self._current_library = libraries[0]
            self._library_view.set_current_library(libraries[0].id)

            await self._load_audiobooks(self._current_client, libraries[0])

            self._status_bar.setText(f"Dossier local: {folder_name}")

        except Exception as e:
            logger.error(f"Failed to load local library: {e}")
            self._status_bar.setText(f"Erreur: {str(e)}")
        finally:
            self._is_loading = False

    async def _load_audiobooks(self, client: Any, library: Library):
        """Load audiobooks from library"""
        self._is_loading = True
        self._status_bar.setText(f"Chargement des audiobooks...")

        try:
            audiobooks = await client.get_audiobooks(library.id, limit=100)

            self._audiobooks = audiobooks
            self._library_view.set_audiobooks(audiobooks)

            self._status_bar.setText(f"{len(audiobooks)} audiobook(s) trouvé(s)")

        except Exception as e:
            logger.error(f"Failed to load audiobooks: {e}")
            self._status_bar.setText(f"Erreur: {str(e)}")
        finally:
            self._is_loading = False

    # Event handlers - Audiobook Selection

    def _on_audiobook_selected(self, audiobook: Audiobook, chapter: Dict[str, Any]):
        """Handle audiobook selection"""
        self._player_view.set_audiobook(audiobook, chapter)

        # Clear and populate queue
        queue.clear()
        for chap in audiobook.chapters:
            queue.add(audiobook, chap)

        queue.set_current(0)

    def _on_audiobook_double_clicked(self, audiobook: Audiobook):
        """Handle audiobook double click - start playing"""
        if audiobook.chapters:
            chapter = audiobook.chapters[0]
            self._on_audiobook_selected(audiobook, chapter)
            self._on_play_pause_clicked()

    # Event handlers - Player Controls

    def _on_play_pause_clicked(self):
        """Handle play/pause click"""
        if player.is_playing():
            player.pause()
        else:
            # Resume or start new playback
            if player.is_paused():
                player.resume()
            else:
                # Get current from queue
                current = queue.get_current()
                if current:
                    audiobook = current["audiobook"]
                    chapter = current["chapter"]
                    player.play(audiobook, chapter)

    def _on_previous_clicked(self):
        """Handle previous chapter click"""
        if player.previous_chapter():
            if not player.is_playing():
                player.play(player._current_audiobook, player._current_chapter)

    def _on_next_clicked(self):
        """Handle next chapter click"""
        if player.next_chapter():
            if not player.is_playing():
                player.play(player._current_audiobook, player._current_chapter)

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
