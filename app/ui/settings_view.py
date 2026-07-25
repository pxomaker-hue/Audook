"""
Settings view for Audook
Allows configuration of servers, preferences, etc.
"""

from PyQt6.QtWidgets import (
 QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
 QLineEdit, QComboBox, QCheckBox, QSlider, QFrame,
 QTabWidget, QScrollArea, QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from typing import List, Optional, Dict, Any

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
 layout.setContentsMargins(15, 15, 15, 15)
 layout.setSpacing(15)
 
 # Server list
 self._server_list_frame = QFrame()
 self._server_list_layout = QVBoxLayout(self._server_list_frame)
 self._server_list_layout.setContentsMargins(10, 10, 10, 10)
 self._server_list_layout.setSpacing(10)
 
 layout.addWidget(QLabel("Configured Servers"))
 layout.addWidget(self._server_list_frame)
 
 # Add server button
 self._add_button = QPushButton("Add Server")
 self._add_button.setStyleSheet("""
 QPushButton {
 background-color: #e94560;
 color: white;
 border: none;
 border-radius: 8px;
 padding: 12px 24px;
 }
 QPushButton:hover {
 background-color: #c73652;
 }
 """)
 self._add_button.clicked.connect(self._on_add_server)
 layout.addWidget(self._add_button)
 
 def _load_servers(self):
 """Load servers from config"""
 self._servers = config_manager.config.servers
 self._update_server_list()
 
 def _update_server_list(self):
 """Update server list display"""
 # Clear existing
 for i in reversed(range(self._server_list_layout.count())):
 widget = self._server_list_layout.itemAt(i).widget()
 if widget:
 widget.deleteLater()
 
 # Add servers
 for server in self._servers:
 server_widget = ServerItemWidget(server, self)
 server_widget.edit_requested.connect(self._on_edit_server)
 server_widget.remove_requested.connect(self._on_remove_server)
 self._server_list_layout.addWidget(server_widget)
 
 def _on_add_server(self):
 """Handle add server"""
 dialog = AddServerDialog(self)
 if dialog.exec() == 1: # Accepted
 server = dialog.get_server()
 if server:
 # Add to config
 config_manager.add_server(server)
 config_manager.config.current_server_id = server.id
 config_manager.save_config()
 
 self._servers = config_manager.config.servers
 self._update_server_list()
 self.server_added.emit(server)
 
 def _on_edit_server(self, server_id: str):
 """Handle edit server"""
 server = self._get_server_by_id(server_id)
 if not server:
 return
 
 dialog = AddServerDialog(self, server)
 if dialog.exec() == 1:
 updated_server = dialog.get_server()
 if updated_server:
 # Update in config
 for i, s in enumerate(config_manager.config.servers):
 if s.id == server_id:
 config_manager.config.servers[i] = updated_server
 break
 config_manager.save_config()
 
 self._servers = config_manager.config.servers
 self._update_server_list()
 self.server_updated.emit(updated_server)
 
 def _on_remove_server(self, server_id: str):
 """Handle remove server"""
 reply = QMessageBox.question(
 self,
 "Remove Server",
 "Are you sure you want to remove this server?",
 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
 )
 
 if reply == QMessageBox.StandardButton.Yes:
 config_manager.remove_server(server_id)
 config_manager.save_config()
 
 self._servers = config_manager.config.servers
 self._update_server_list()
 self.server_removed.emit(server_id)
 
 def _get_server_by_id(self, server_id: str) -> Optional[ServerConfig]:
 """Get server by ID"""
 for server in self._servers:
 if server.id == server_id:
 return server
 return None


class ServerItemWidget(QWidget):
 """Widget for displaying a server in the list"""
 
 edit_requested = pyqtSignal(str)
 remove_requested = pyqtSignal(str)
 
 def __init__(self, server: ServerConfig, parent=None):
 super().__init__(parent)
 self._server = server
 self._init_ui()
 
 def _init_ui(self):
 """Initialize UI"""
 layout = QHBoxLayout(self)
 layout.setContentsMargins(10, 10, 10, 10)
 layout.setSpacing(10)
 
 # Server info
 info_layout = QVBoxLayout()
 info_layout.setSpacing(2)
 
 self._name_label = QLabel(self._server.name)
 self._name_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
 self._name_label.setStyleSheet("color: #eaeaea;")
 
 self._type_label = QLabel(f"Type: {self._server.type}")
 self._type_label.setFont(QFont("Segoe UI", 12))
 self._type_label.setStyleSheet("color: #888888;")
 
 self._url_label = QLabel(self._server.url)
 self._url_label.setFont(QFont("Segoe UI", 10))
 self._url_label.setStyleSheet("color: #666666;")
 self._url_label.setWordWrap(True)
 
 info_layout.addWidget(self._name_label)
 info_layout.addWidget(self._type_label)
 info_layout.addWidget(self._url_label)
 
 # Buttons
 button_layout = QHBoxLayout()
 button_layout.setSpacing(5)
 
 self._edit_button = QPushButton("Edit")
 self._edit_button.setFixedWidth(80)
 self._edit_button.setStyleSheet("""
 QPushButton {
 background-color: #1a4a7a;
 color: white;
 border: none;
 border-radius: 6px;
 padding: 8px 16px;
 }
 """)
 self._edit_button.clicked.connect(self._on_edit)
 
 self._remove_button = QPushButton("Remove")
 self._remove_button.setFixedWidth(80)
 self._remove_button.setStyleSheet("""
 QPushButton {
 background-color: #e94560;
 color: white;
 border: none;
 border-radius: 6px;
 padding: 8px 16px;
 }
 """)
 self._remove_button.clicked.connect(self._on_remove)
 
 button_layout.addWidget(self._edit_button)
 button_layout.addWidget(self._remove_button)
 
 layout.addLayout(info_layout)
 layout.addStretch()
 layout.addLayout(button_layout)
 
 self.setStyleSheet("""
 ServerItemWidget {
 background-color: #16213e;
 border: 1px solid #1a4a7a;
 border-radius: 8px;
 }
 """)
 
 def _on_edit(self):
 """Handle edit button click"""
 self.edit_requested.emit(self._server.id)
 
 def _on_remove(self):
 """Handle remove button click"""
 self.remove_requested.emit(self._server.id)


class AddServerDialog(QWidget):
 """Dialog for adding/editing a server"""
 
 def __init__(self, parent=None, server: Optional[ServerConfig] = None):
 super().__init__(parent)
 self._server = server
 self._init_ui()
 
 if server:
 self._populate_form()
 
 def _init_ui(self):
 """Initialize UI"""
 self.setWindowTitle("Add Server" if not self._server else "Edit Server")
 self.setMinimumWidth(400)
 
 layout = QVBoxLayout(self)
 layout.setContentsMargins(20, 20, 20, 20)
 layout.setSpacing(15)
 
 # Form
 form_layout = QFormLayout()
 form_layout.setSpacing(10)
 
 # Name
 self._name_edit = QLineEdit()
 self._name_edit.setStyleSheet("""
 QLineEdit {
 background-color: #0f3460;
 color: #eaeaea;
 border: 1px solid #1a4a7a;
 border-radius: 6px;
 padding: 8px 12px;
 }
 """)
 form_layout.addRow("Name:", self._name_edit)
 
 # Type
 self._type_combo = QComboBox()
 self._type_combo.addItems(["Audiobookshelf", "Plex"])
 self._type_combo.setStyleSheet("""
 QComboBox {
 background-color: #0f3460;
 color: #eaeaea;
 border: 1px solid #1a4a7a;
 border-radius: 6px;
 padding: 8px 12px;
 }
 """)
 form_layout.addRow("Type:", self._type_combo)
 
 # URL
 self._url_edit = QLineEdit()
 self._url_edit.setPlaceholderText("http://your-server:port")
 self._url_edit.setStyleSheet("""
 QLineEdit {
 background-color: #0f3460;
 color: #eaeaea;
 border: 1px solid #1a4a7a;
 border-radius: 6px;
 padding: 8px 12px;
 }
 """)
 form_layout.addRow("URL:", self._url_edit)
 
 # API Key (for Audiobookshelf)
 self._api_key_edit = QLineEdit()
 self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
 self._api_key_edit.setStyleSheet("""
 QLineEdit {
 background-color: #0f3460;
 color: #eaeaea;
 border: 1px solid #1a4a7a;
 border-radius: 6px;
 padding: 8px 12px;
 }
 """)
 form_layout.addRow("API Key:", self._api_key_edit)
 
 # Username (for Plex)
 self._username_edit = QLineEdit()
 self._username_edit.setStyleSheet("""
 QLineEdit {
 background-color: #0f3460;
 color: #eaeaea;
 border: 1px solid #1a4a7a;
 border-radius: 6px;
 padding: 8px 12px;
 }
 """)
 form_layout.addRow("Username:", self._username_edit)
 
 # Password (for Plex)
 self._password_edit = QLineEdit()
 self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
 self._password_edit.setStyleSheet("""
 QLineEdit {
 background-color: #0f3460;
 color: #eaeaea;
 border: 1px solid #1a4a7a;
 border-radius: 6px;
 padding: 8px 12px;
 }
 """)
 form_layout.addRow("Password:", self._password_edit)
 
 layout.addLayout(form_layout)
 
 # Buttons
 button_layout = QHBoxLayout()
 button_layout.setSpacing(10)
 
 self._cancel_button = QPushButton("Cancel")
 self._cancel_button.setFixedWidth(100)
 self._cancel_button.setStyleSheet("""
 QPushButton {
 background-color: #0f3460;
 color: white;
 border: none;
 border-radius: 6px;
 padding: 10px 20px;
 }
 """)
 self._cancel_button.clicked.connect(self.close)
 
 self._save_button = QPushButton("Save")
 self._save_button.setFixedWidth(100)
 self._save_button.setStyleSheet("""
 QPushButton {
 background-color: #e94560;
 color: white;
 border: none;
 border-radius: 6px;
 padding: 10px 20px;
 }
 """)
 self._save_button.clicked.connect(self.accept)
 
 button_layout.addStretch()
 button_layout.addWidget(self._cancel_button)
 button_layout.addWidget(self._save_button)
 
 layout.addLayout(button_layout)
 
 # Connect type combo to update fields
 self._type_combo.currentTextChanged.connect(self._on_type_changed)
 
 def _populate_form(self):
 """Populate form with server data"""
 if not self._server:
 return
 
 self._name_edit.setText(self._server.name)
 
 if self._server.type == "audiobookshelf":
 self._type_combo.setCurrentIndex(0)
 else:
 self._type_combo.setCurrentIndex(1)
 
 self._url_edit.setText(self._server.url)
 self._api_key_edit.setText(self._server.api_key or "")
 self._username_edit.setText(self._server.username or "")
 self._password_edit.setText(self._server.password or "")
 
 self._on_type_changed(self._type_combo.currentText())
 
 def _on_type_changed(self, text: str):
 """Handle type combo change"""
 is_audiobookshelf = text == "Audiobookshelf"
 
 # Show/hide fields based on type
 self._api_key_edit.setVisible(is_audiobookshelf)
 self._username_edit.setVisible(not is_audiobookshelf)
 self._password_edit.setVisible(not is_audiobookshelf)
 
 def get_server(self) -> Optional[ServerConfig]:
 """Get server from form"""
 name = self._name_edit.text().strip()
 if not name:
 QMessageBox.warning(self, "Error", "Please enter a server name")
 return None
 
 url = self._url_edit.text().strip()
 if not url:
 QMessageBox.warning(self, "Error", "Please enter a server URL")
 return None
 
 server_type = "audiobookshelf" if self._type_combo.currentText() == "Audiobookshelf" else "plex"
 
 if self._server:
 server_id = self._server.id
 else:
 from app.utils import generate_id
 server_id = generate_id("server_")
 
 return ServerConfig(
 id=server_id,
 name=name,
 type=server_type,
 url=url,
 api_key=self._api_key_edit.text().strip() if server_type == "audiobookshelf" else None,
 username=self._username_edit.text().strip() if server_type == "plex" else None,
 password=self._password_edit.text().strip() if server_type == "plex" else None
 )
 
 def accept(self):
 """Handle accept"""
 server = self.get_server()
 if server:
 super().accept()
 
 def reject(self):
 """Handle reject"""
 super().reject()


class PreferencesWidget(QWidget):
 """Widget for application preferences"""
 
 preferences_changed = pyqtSignal()
 
 def __init__(self, parent=None):
 super().__init__(parent)
 self._init_ui()
 self._load_preferences()
 
 def _init_ui(self):
 """Initialize UI"""
 layout = QVBoxLayout(self)
 layout.setContentsMargins(15, 15, 15, 15)
 layout.setSpacing(15)
 
 # Scroll area
 scroll_area = QScrollArea()
 scroll_area.setWidgetResizable(True)
 scroll_area.setStyleSheet("""
 QScrollArea {
 background-color: transparent;
 border: none;
 }
 """)
 
 scroll_widget = QWidget()
 scroll_layout = QVBoxLayout(scroll_widget)
 scroll_layout.setContentsMargins(10, 10, 10, 10)
 scroll_layout.setSpacing(20)
 
 # Appearance section
 appearance_frame = QFrame()
 appearance_layout = QVBoxLayout(appearance_frame)
 appearance_layout.setContentsMargins(15, 15, 15, 15)
 appearance_layout.setSpacing(10)
 
 appearance_label = QLabel("Appearance")
 appearance_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
 appearance_layout.addWidget(appearance_label)
 
 # Theme
 theme_layout = QHBoxLayout()
 theme_layout.setSpacing(10)
 
 theme_label = QLabel("Theme:")
 theme_label.setStyleSheet("color: #eaeaea;")
 
 self._theme_combo = QComboBox()
 self._theme_combo.addItems(["Dark", "Light"])
 self._theme_combo.setStyleSheet("""
 QComboBox {
 background-color: #0f3460;
 color: #eaeaea;
 border: 1px solid #1a4a7a;
 border-radius: 6px;
 padding: 8px 12px;
 }
 """)
 
 theme_layout.addWidget(theme_label)
 theme_layout.addWidget(self._theme_combo)
 appearance_layout.addLayout(theme_layout)
 
 # Playback section
 playback_frame = QFrame()
 playback_layout = QVBoxLayout(playback_frame)
 playback_layout.setContentsMargins(15, 15, 15, 15)
 playback_layout.setSpacing(10)
 
 playback_label = QLabel("Playback")
 playback_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
 playback_layout.addWidget(playback_label)
 
 # Remember position
 self._remember_position_check = QCheckBox("Remember playback position")
 self._remember_position_check.setStyleSheet("""
 QCheckBox {
 color: #eaeaea;
 spacing: 8px;
 }
 QCheckBox::indicator {
 width: 18px;
 height: 18px;
 }
 """)
 playback_layout.addWidget(self._remember_position_check)
 
 # Sync with server
 self._sync_check = QCheckBox("Sync playback position with server")
 self._sync_check.setStyleSheet("""
 QCheckBox {
 color: #eaeaea;
 spacing: 8px;
 }
 """)
 playback_layout.addWidget(self._sync_check)
 
 # Default volume
 volume_layout = QHBoxLayout()
 volume_layout.setSpacing(10)
 
 volume_label = QLabel("Default Volume:")
 volume_label.setStyleSheet("color: #eaeaea;")
 
 self._volume_slider = QSlider(Qt.Orientation.Horizontal)
 self._volume_slider.setRange(0, 100)
 self._volume_slider.setStyleSheet("""
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
 """)
 
 self._volume_label = QLabel("80%")
 self._volume_label.setStyleSheet("color: #888888;")
 
 volume_layout.addWidget(volume_label)
 volume_layout.addWidget(self._volume_slider)
 volume_layout.addWidget(self._volume_label)
 playback_layout.addLayout(volume_layout)
 
 # Default speed
 speed_layout = QHBoxLayout()
 speed_layout.setSpacing(10)
 
 speed_label = QLabel("Default Speed:")
 speed_label.setStyleSheet("color: #eaeaea;")
 
 self._speed_combo = QComboBox()
 self._speed_combo.addItems(["0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x"])
 self._speed_combo.setStyleSheet("""
 QComboBox {
 background-color: #0f3460;
 color: #eaeaea;
 border: 1px solid #1a4a7a;
 border-radius: 6px;
 padding: 8px 12px;
 }
 """)
 
 speed_layout.addWidget(speed_label)
 speed_layout.addWidget(self._speed_combo)
 playback_layout.addLayout(speed_layout)
 
 # Download quality
 quality_layout = QHBoxLayout()
 quality_layout.setSpacing(10)
 
 quality_label = QLabel("Download Quality:")
 quality_label.setStyleSheet("color: #eaeaea;")
 
 self._quality_combo = QComboBox()
 self._quality_combo.addItems(["High", "Medium", "Low"])
 self._quality_combo.setStyleSheet("""
 QComboBox {
 background-color: #0f3460;
 color: #eaeaea;
 border: 1px solid #1a4a7a;
 border-radius: 6px;
 padding: 8px 12px;
 }
 """)
 
 quality_layout.addWidget(quality_label)
 quality_layout.addWidget(self._quality_combo)
 playback_layout.addLayout(quality_layout)
 
 # Add sections to scroll layout
 scroll_layout.addWidget(appearance_frame)
 scroll_layout.addWidget(playback_frame)
 scroll_layout.addStretch()
 
 scroll_area.setWidget(scroll_widget)
 layout.addWidget(scroll_area)
 
 # Save button
 self._save_button = QPushButton("Save Preferences")
 self._save_button.setStyleSheet("""
 QPushButton {
 background-color: #e94560;
 color: white;
 border: none;
 border-radius: 8px;
 padding: 12px 24px;
 }
 """)
 self._save_button.clicked.connect(self._on_save)
 layout.addWidget(self._save_button)
 
 # Connections
 self._volume_slider.valueChanged.connect(self._on_volume_changed)
 
 def _load_preferences(self):
 """Load preferences from config"""
 config = config_manager.config
 
 # Theme
 index = self._theme_combo.findText(config.theme.capitalize())
 if index >= 0:
 self._theme_combo.setCurrentIndex(index)
 
 # Remember position
 self._remember_position_check.setChecked(config.remember_position)
 
 # Sync
 self._sync_check.setChecked(config.sync_enabled)
 
 # Volume
 self._volume_slider.setValue(int(config.volume * 100))
 self._volume_label.setText(f"{int(config.volume * 100)}%")
 
 # Speed
 speed_text = f"{config.playback_speed}x"
 index = self._speed_combo.findText(speed_text)
 if index >= 0:
 self._speed_combo.setCurrentIndex(index)
 
 # Quality
 index = self._quality_combo.findText(config.download_quality.capitalize())
 if index >= 0:
 self._quality_combo.setCurrentIndex(index)
 
 def _on_volume_changed(self, value: int):
 """Handle volume slider change"""
 self._volume_label.setText(f"{value}%")
 
 def _on_save(self):
 """Handle save button click"""
 config = config_manager.config
 
 # Theme
 config.theme = self._theme_combo.currentText().lower()
 
 # Remember position
 config.remember_position = self._remember_position_check.isChecked()
 
 # Sync
 config.sync_enabled = self._sync_check.isChecked()
 
 # Volume
 config.volume = self._volume_slider.value() / 100.0
 
 # Speed
 speed_text = self._speed_combo.currentText()
 config.playback_speed = float(speed_text.replace("x", ""))
 
 # Quality
 config.download_quality = self._quality_combo.currentText().lower()
 
 config_manager.save_config()
 
 self.preferences_changed.emit()
 QMessageBox.information(self, "Saved", "Preferences saved successfully")


class SettingsView(QTabWidget):
 """Main settings view with tabs"""
 
 def __init__(self, parent=None):
 super().__init__(parent)
 self._init_ui()
 
 def _init_ui(self):
 """Initialize UI"""
 self.setStyleSheet("""
 QTabWidget::pane {
 background-color: #16213e;
 border: 1px solid #1a4a7a;
 border-radius: 8px;
 }
 QTabWidget::tab-bar {
 background-color: #0f3460;
 border-radius: 8px;
 }
 QTabBar::tab {
 background-color: #0f3460;
 color: #eaeaea;
 padding: 12px 24px;
 border: none;
 border-radius: 8px;
 }
 QTabBar::tab:selected {
 background-color: #e94560;
 color: white;
 }
 QTabBar::tab:hover {
 background-color: #1a4a7a;
 }
 """)
 
 # Add tabs
 self._server_settings = ServerSettingsWidget(self)
 self.addTab(self._server_settings, "Servers")
 
 self._preferences = PreferencesWidget(self)
 self.addTab(self._preferences, "Preferences")
 
 # Connect signals
 self._preferences.preferences_changed.connect(self._on_preferences_changed)
 
 def _on_preferences_changed(self):
 """Handle preferences changed"""
 # Apply theme change
 from app.ui import apply_theme
 from PyQt6.QtWidgets import QApplication
 
 app = QApplication.instance()
 if app:
 apply_theme(app, config_manager.config.theme)
