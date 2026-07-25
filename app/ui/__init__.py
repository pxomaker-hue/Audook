"""
UI components for Audook
"""

from PyQt6.QtWidgets import QApplication

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
}

QPushButton:hover {
    background-color: #1a4a7a;
}

QPushButton:pressed {
    background-color: #0a2845;
}

QLineEdit {
    background-color: #0f3460;
    color: #eaeaea;
    border: 1px solid #1a4a7a;
    border-radius: 8px;
    padding: 10px 15px;
    font-size: 14px;
}

QComboBox {
    background-color: #0f3460;
    color: #eaeaea;
    border: 1px solid #1a4a7a;
    border-radius: 8px;
    padding: 10px 15px;
    font-size: 14px;
}

QComboBox QAbstractItemView {
    background-color: #0f3460;
    color: #eaeaea;
    selection-background-color: #1a4a7a;
}

QSlider::groove:horizontal {
    background-color: #0f3460;
    border-radius: 5px;
    height: 8px;
}

QSlider::handle:horizontal {
    background-color: #e94560;
    border-radius: 5px;
    width: 16px;
    margin: -4px 0;
}

QSlider::handle:horizontal:hover {
    background-color: #ff5a77;
}

QLabel {
    color: #eaeaea;
}

QSpinBox, QDoubleSpinBox {
    background-color: #0f3460;
    color: #eaeaea;
    border: 1px solid #1a4a7a;
    border-radius: 8px;
    padding: 10px 15px;
}

QCheckBox {
    color: #eaeaea;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
}

QCheckBox::indicator:unchecked {
    background-color: #0f3460;
    border: 1px solid #1a4a7a;
    border-radius: 4px;
}

QCheckBox::indicator:checked {
    background-color: #e94560;
    border: 1px solid #e94560;
    border-radius: 4px;
}
"""

STYLESHEET_LIGHT = """
QMainWindow {
    background-color: #ffffff;
}

QWidget {
    background-color: #f5f5f5;
    color: #000000;
    font-family: 'Segoe UI', Arial, sans-serif;
}

QPushButton {
    background-color: #007bff;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 12px 24px;
    font-size: 14px;
}

QPushButton:hover {
    background-color: #0056b3;
}

QPushButton:pressed {
    background-color: #003d82;
}

QLineEdit {
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #cccccc;
    border-radius: 8px;
    padding: 10px 15px;
    font-size: 14px;
}

QComboBox {
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #cccccc;
    border-radius: 8px;
    padding: 10px 15px;
    font-size: 14px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #000000;
    selection-background-color: #e8f4f8;
}

QSlider::groove:horizontal {
    background-color: #e0e0e0;
    border-radius: 5px;
    height: 8px;
}

QSlider::handle:horizontal {
    background-color: #e94560;
    border-radius: 5px;
    width: 16px;
    margin: -4px 0;
}

QSlider::handle:horizontal:hover {
    background-color: #ff5a77;
}

QLabel {
    color: #000000;
}

QSpinBox, QDoubleSpinBox {
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #cccccc;
    border-radius: 8px;
    padding: 10px 15px;
}

QCheckBox {
    color: #000000;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
}

QCheckBox::indicator:unchecked {
    background-color: #ffffff;
    border: 1px solid #cccccc;
    border-radius: 4px;
}

QCheckBox::indicator:checked {
    background-color: #e94560;
    border: 1px solid #e94560;
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
    stylesheet = get_stylesheet(theme)
    app.setStyleSheet(stylesheet)
