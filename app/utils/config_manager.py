"""
Configuration manager for Audook
Handles loading, saving, and managing application configuration
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from app.models import AppConfig, ServerConfig, PlaybackState, Bookmark
from app.utils import save_json, load_json, logger
from app import CONFIG_FILE, DATA_DIR


class ConfigManager:
    """Manages application configuration"""
    
    def __init__(self):
        self.config: AppConfig = AppConfig()
        self.playback_state: Optional[PlaybackState] = None
        self.bookmarks: Dict[str, Bookmark] = {}
        self._load_all()
    
    def _load_all(self):
        """Load all configuration files"""
        self._load_config()
        self._load_playback_state()
        self._load_bookmarks()
    
    def _load_config(self):
        """Load main configuration"""
        data = load_json(CONFIG_FILE)
        if data:
            try:
                self.config = AppConfig(**data)
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                self.config = AppConfig()
    
    def _load_playback_state(self):
        """Load playback state"""
        state_file = DATA_DIR / "playback_state.json"
        data = load_json(state_file)
        if data:
            try:
                self.playback_state = PlaybackState(**data)
            except Exception as e:
                logger.error(f"Failed to load playback state: {e}")
    
    def _load_bookmarks(self):
        """Load bookmarks"""
        bookmarks_file = DATA_DIR / "bookmarks.json"
        data = load_json(bookmarks_file)
        if data:
            try:
                for book_id, bookmark_data in data.items():
                    self.bookmarks[book_id] = Bookmark(**bookmark_data)
            except Exception as e:
                logger.error(f"Failed to load bookmarks: {e}")
    
    def save_config(self) -> bool:
        """Save main configuration"""
        return save_json(CONFIG_FILE, self.config.model_dump())
    
    def save_playback_state(self) -> bool:
        """Save playback state"""
        if not self.playback_state:
            return False
        state_file = DATA_DIR / "playback_state.json"
        return save_json(state_file, self.playback_state.model_dump())
    
    def save_bookmarks(self) -> bool:
        """Save all bookmarks"""
        bookmarks_file = DATA_DIR / "bookmarks.json"
        bookmarks_data = {book_id: bm.model_dump() for book_id, bm in self.bookmarks.items()}
        return save_json(bookmarks_file, bookmarks_data)
    
    def add_bookmark(self, bookmark: Bookmark) -> bool:
        """Add or update a bookmark"""
        self.bookmarks[bookmark.book_id] = bookmark
        return self.save_bookmarks()
    
    def remove_bookmark(self, book_id: str) -> bool:
        """Remove a bookmark"""
        if book_id in self.bookmarks:
            del self.bookmarks[book_id]
            return self.save_bookmarks()
        return False
    
    def get_bookmark(self, book_id: str) -> Optional[Bookmark]:
        """Get a bookmark by book ID"""
        return self.bookmarks.get(book_id)
    
    def update_playback_state(self, state: PlaybackState):
        """Update playback state"""
        self.playback_state = state
        if self.config.remember_position:
            self.save_playback_state()
    
    def add_server(self, server: ServerConfig) -> bool:
        """Add a new server configuration"""
        # Check if server with same URL already exists
        for existing in self.config.servers:
            if existing.url == server.url and existing.type == server.type:
                return False
        
        self.config.servers.append(server)
        if not self.config.current_server_id:
            self.config.current_server_id = server.id
        return self.save_config()
    
    def remove_server(self, server_id: str) -> bool:
        """Remove a server configuration"""
        self.config.servers = [s for s in self.config.servers if s.id != server_id]
        if self.config.current_server_id == server_id:
            self.config.current_server_id = None
        return self.save_config()
    
    def get_current_server(self) -> Optional[ServerConfig]:
        """Get the currently selected server"""
        if not self.config.current_server_id:
            return None
        for server in self.config.servers:
            if server.id == self.config.current_server_id:
                return server
        return None
    
    def set_current_server(self, server_id: str) -> bool:
        """Set the current server"""
        # Check if server exists
        for server in self.config.servers:
            if server.id == server_id:
                self.config.current_server_id = server_id
                return self.save_config()
        return False
    
    def get_server_by_id(self, server_id: str) -> Optional[ServerConfig]:
        """Get a server by ID"""
        for server in self.config.servers:
            if server.id == server_id:
                return server
        return None


# Global config manager instance
config_manager = ConfigManager()
