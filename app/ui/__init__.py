"""
UI components for Audook
"""

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont, QPalette, QColor

# Application styles
STYLESHEET_DARK = """
QMainWindow {
 background-color: #1a1a2e;
}

QWidget {
 background-color: #16213e;
 color: #eaeaea;
 font-family: 'Segoe UI', Arial, sans-serif;
}

QPushButton {
 background-color: #0f3460;
 color: #eaeaea;
 border: none;
 border-radius: 8px;
 padding: 12px 24px;
 font-size: 14px;
 transition: background-color 0.2s;
}

QPushButton:hover {
 background-color: #1a4a7a;
}

QPushButton:pressed {
 background-color: #0a2845;
}

QPushButton:disabled {
 background-color: #0a2845;
 color: #6c757d;
}

QLineEdit {
 background-color: #0f3460;
 color: #eaeaea;
 border: 1px solid #1a4a7a;
 border-radius: 8px;
 padding: 10px 15px;
 font-size: 14px;
}

QLineEdit:focus {
 border: 2px solid #e94560;
}

QLabel {
 color: #eaeaea;
 font-size: 14px;
}

QListWidget {
 background-color: #0f3460;
 color: #eaeaea;
 border: 1px solid #1a4a7a;
 border-radius: 8px;
 padding: 5px;
}

QListWidget::item {
 padding: 10px;
 border-radius: 4px;
}

QListWidget::item:selected {
 background-color: #e94560;
 color: white;
}

QListWidget::item:hover {
 background-color: #1a4a7a;
}

QScrollBar:vertical {
 background-color: #0f3460;
 border-radius: 4px;
 width: 8px;
}

QScrollBar::handle:vertical {
 background-color: #1a4a7a;
 border-radius: 4px;
 min-height: 20px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
 background: none;
 border: none;
}

QComboBox {
 background-color: #0f3460;
 color: #eaeaea;
 border: 1px solid #1a4a7a;
 border-radius: 8px;
 padding: 10px 15px;
 font-size: 14px;
}

QComboBox::drop-down {
 border: none;
}

QComboBox QAbstractItemView {
 background-color: #0f3460;
 color: #eaeaea;
 selection-background-color: #e94560;
 selection-color: white;
}

QSlider::groove:horizontal {
 background-color: #0f3460;
 height: 8px;
 border-radius: 4px;
}

QSlider::handle:horizontal {
 background-color: #e94560;
 width: 16px;
 height: 16px;
 border-radius: 8px;
 margin: -4px 0;
}

QSlider::add-page:horizontal {
 background-color: #1a4a7a;
 border-radius: 4px;
}

QSlider::sub-page:horizontal {
 background-color: #e94560;
 border-radius: 4px;
}

QProgressBar {
 background-color: #0f3460;
 border: 1px solid #1a4a7a;
 border-radius: 4px;
 text-align: center;
}

QProgressBar::chunk {
 background-color: #e94560;
 border-radius: 4px;
}

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

QFrame {
 background-color: #0f3460;
 border-radius: 8px;
}

QToolButton {
 background-color: transparent;
 color: #eaeaea;
 border: none;
 padding: 8px;
}

QToolButton:hover {
 background-color: #1a4a7a;
 border-radius: 4px;
}

QToolButton:pressed {
 background-color: #0a2845;
 border-radius: 4px;
}
"""

STYLESHEET_LIGHT = """
QMainWindow {
 background-color: #f5f5f5;
}

QWidget {
 background-color: #ffffff;
 color: #333333;
 font-family: 'Segoe UI', Arial, sans-serif;
}

QPushButton {
 background-color: #e94560;
 color: white;
 border: none;
 border-radius: 8px;
 padding: 12px 24px;
 font-size: 14px;
 transition: background-color 0.2s;
}

QPushButton:hover {
 background-color: #c73652;
}

QPushButton:pressed {
 background-color: #a52840;
}

QPushButton:disabled {
 background-color: #cccccc;
 color: #6c757d;
}

QLineEdit {
 background-color: #f8f9fa;
 color: #333333;
 border: 1px solid #ced4da;
 border-radius: 8px;
 padding: 10px 15px;
 font-size: 14px;
}

QLineEdit:focus {
 border: 2px solid #e94560;
}

QLabel {
 color: #333333;
 font-size: 14px;
}

QListWidget {
 background-color: #f8f9fa;
 color: #333333;
 border: 1px solid #ced4da;
 border-radius: 8px;
 padding: 5px;
}

QListWidget::item {
 padding: 10px;
 border-radius: 4px;
}

QListWidget::item:selected {
 background-color: #e94560;
 color: white;
}

QListWidget::item:hover {
 background-color: #f1f1f1;
}

QScrollBar:vertical {
 background-color: #f1f1f1;
 border-radius: 4px;
 width: 8px;
}

QScrollBar::handle:vertical {
 background-color: #ced4da;
 border-radius: 4px;
 min-height: 20px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
 background: none;
 border: none;
}

QComboBox {
 background-color: #f8f9fa;
 color: #333333;
 border: 1px solid #ced4da;
 border-radius: 8px;
 padding: 10px 15px;
 font-size: 14px;
}

QComboBox::drop-down {
 border: none;
}

QComboBox QAbstractItemView {
 background-color: #f8f9fa;
 color: #333333;
 selection-background-color: #e94560;
 selection-color: white;
}

QSlider::groove:horizontal {
 background-color: #f1f1f1;
 height: 8px;
 border-radius: 4px;
}

QSlider::handle:horizontal {
 background-color: #e94560;
 width: 16px;
 height: 16px;
 border-radius: 8px;
 margin: -4px 0;
}

QSlider::add-page:horizontal {
 background-color: #ced4da;
 border-radius: 4px;
}

QSlider::sub-page:horizontal {
 background-color: #e94560;
 border-radius: 4px;
}

QProgressBar {
 background-color: #f1f1f1;
 border: 1px solid #ced4da;
 border-radius: 4px;
 text-align: center;
}

QProgressBar::chunk {
 background-color: #e94560;
 border-radius: 4px;
}

QTabWidget::pane {
 background-color: #ffffff;
 border: 1px solid #ced4da;
 border-radius: 8px;
}

QTabWidget::tab-bar {
 background-color: #f8f9fa;
 border-radius: 8px;
}

QTabBar::tab {
 background-color: #f8f9fa;
 color: #333333;
 padding: 12px 24px;
 border: none;
 border-radius: 8px;
}

QTabBar::tab:selected {
 background-color: #e94560;
 color: white;
}

QTabBar::tab:hover {
 background-color: #e9ecef;
}

QFrame {
 background-color: #f8f9fa;
 border-radius: 8px;
}

QToolButton {
 background-color: transparent;
 color: #333333;
 border: none;
 padding: 8px;
}

QToolButton:hover {
 background-color: #e9ecef;
 border-radius: 4px;
}

QToolButton:pressed {
 background-color: #dee2e6;
 border-radius: 4px;
}
"""


def get_stylesheet(theme: str = "dark") -> str:
 """Get stylesheet based on theme"""
 if theme == "light":
 return STYLESHEET_LIGHT
 return STYLESHEET_DARK


def apply_theme(app: QApplication, theme: str = "dark"):
 """Apply theme to application"""
 if theme == "light":
 palette = QPalette()
 palette.setColor(QPalette.ColorRole.Window, QColor(255, 255, 255))
 palette.setColor(QPalette.ColorRole.WindowText, QColor(51, 51, 51))
 palette.setColor(QPalette.ColorRole.Base, QColor(248, 249, 250))
 palette.setColor(QPalette.ColorRole.AlternateBase, QColor(241, 241, 241))
 palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
 palette.setColor(QPalette.ColorRole.ToolTipText, QColor(51, 51, 51))
 palette.setColor(QPalette.ColorRole.Text, QColor(51, 51, 51))
 palette.setColor(QPalette.ColorRole.Button, QColor(233, 69, 96))
 palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
 palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
 palette.setColor(QPalette.ColorRole.Link, QColor(233, 69, 96))
 palette.setColor(QPalette.ColorRole.Highlight, QColor(233, 69, 96))
 palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
 app.setPalette(palette)
 else:
 palette = QPalette()
 palette.setColor(QPalette.ColorRole.Window, QColor(22, 33, 62))
 palette.setColor(QPalette.ColorRole.WindowText, QColor(234, 234, 234))
 palette.setColor(QPalette.ColorRole.Base, QColor(15, 52, 96))
 palette.setColor(QPalette.ColorRole.AlternateBase, QColor(26, 74, 122))
 palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(22, 33, 62))
 palette.setColor(QPalette.ColorRole.ToolTipText, QColor(234, 234, 234))
 palette.setColor(QPalette.ColorRole.Text, QColor(234, 234, 234))
 palette.setColor(QPalette.ColorRole.Button, QColor(15, 52, 96))
 palette.setColor(QPalette.ColorRole.ButtonText, QColor(234, 234, 234))
 palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
 palette.setColor(QPalette.ColorRole.Link, QColor(233, 69, 96))
 palette.setColor(QPalette.ColorRole.Highlight, QColor(233, 69, 96))
 palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
 app.setPalette(palette)
 
 app.setStyleSheet(get_stylesheet(theme))
