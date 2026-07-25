"""
Settings view for Audook
"""

from PyQt6.QtWidgets import QWidget, QDialog, QVBoxLayout, QLabel, QTabWidget
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont
from typing import List

from app.models import ServerConfig
from app.utils.config_manager import config_manager


class ServerSettingsWidget(QWidget):
    """Widget for server settings"""

    server_added = pyqtSignal(ServerConfig)
    server_updated = pyqtSignal(ServerConfig)
    server_removed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._servers: List[ServerConfig] = []
        self._init_ui()
        self._load_servers()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        label = QLabel("Paramètres des serveurs")
        label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(label)

    def _load_servers(self):
        """Load servers from config"""
        self._servers = config_manager.config.servers


class SettingsView(QDialog):
    """Settings dialog"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._server_settings = ServerSettingsWidget()
        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Tab widget
        tabs = QTabWidget()
        tabs.addTab(self._server_settings, "Serveurs")

        # Preferences tab (placeholder)
        prefs_widget = QWidget()
        prefs_layout = QVBoxLayout(prefs_widget)
        prefs_label = QLabel("Préférences")
        prefs_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        prefs_layout.addWidget(prefs_label)
        tabs.addTab(prefs_widget, "Préférences")

        layout.addWidget(tabs)
