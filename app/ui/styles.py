"""
UI Stylesheet definitions for Audook
Modern, clean design with good spacing
"""

MAIN_STYLESHEET = """
QMainWindow {
    background-color: #fafafa;
}

/* Sidebar */
QWidget#sidebar {
    background-color: #ffffff;
    border-right: 1px solid #e0e0e0;
}

QPushButton#sidebar_btn {
    background-color: transparent;
    border: none;
    color: #666666;
    padding: 12px 16px;
    text-align: left;
    font-size: 14px;
    font-weight: 500;
}

QPushButton#sidebar_btn:hover {
    background-color: #f5f5f5;
    color: #333333;
}

QPushButton#sidebar_btn:pressed,
QPushButton#sidebar_btn.active {
    background-color: #f0f0f0;
    color: #000000;
    border-left: 3px solid #ffd700;
    padding-left: 13px;
}

/* Main content */
QWidget#content_area {
    background-color: #fafafa;
}

/* Labels and text */
QLabel#title {
    color: #000000;
    font-size: 24px;
    font-weight: bold;
}

QLabel#subtitle {
    color: #666666;
    font-size: 14px;
}

QLabel#section_title {
    color: #000000;
    font-size: 18px;
    font-weight: 600;
}

/* Search */
QLineEdit#search_box {
    background-color: #f5f5f5;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 14px;
    color: #333333;
    selection-background-color: #ffd700;
}

QLineEdit#search_box:focus {
    border: 1px solid #cccccc;
    background-color: #ffffff;
}

QLineEdit#search_box::placeholder {
    color: #999999;
}

/* Scroll area */
QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollBar:vertical {
    background-color: #fafafa;
    width: 8px;
    border: none;
}

QScrollBar::handle:vertical {
    background-color: #d0d0d0;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #b0b0b0;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

/* Buttons */
QPushButton#primary_btn {
    background-color: #000000;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: 600;
}

QPushButton#primary_btn:hover {
    background-color: #333333;
}

QPushButton#primary_btn:pressed {
    background-color: #000000;
}

QPushButton#icon_btn {
    background-color: transparent;
    border: none;
    color: #666666;
    padding: 8px;
}

QPushButton#icon_btn:hover {
    background-color: #f0f0f0;
    border-radius: 4px;
}

/* Player controls */
QWidget#player_bar {
    background-color: #ffffff;
    border-top: 1px solid #e0e0e0;
}

QSlider::groove:horizontal {
    background-color: #e0e0e0;
    height: 4px;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background-color: #000000;
    width: 14px;
    margin: -5px 0px;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background-color: #333333;
}

QLabel#time_label {
    color: #999999;
    font-size: 12px;
}

/* Rating */
QLabel#rating {
    color: #ffc107;
    font-size: 12px;
}

/* Card */
QWidget#book_card {
    background-color: #ffffff;
    border: 1px solid #f0f0f0;
    border-radius: 12px;
}

QWidget#book_card:hover {
    border: 1px solid #e0e0e0;
}
"""

# Color palette
COLORS = {
    "primary": "#000000",
    "primary_light": "#333333",
    "background": "#fafafa",
    "surface": "#ffffff",
    "surface_variant": "#f5f5f5",
    "border": "#e0e0e0",
    "text": "#000000",
    "text_secondary": "#666666",
    "text_tertiary": "#999999",
    "accent": "#ffd700",
}

# Typography
FONTS = {
    "title": ("Segoe UI", 24, "bold"),
    "subtitle": ("Segoe UI", 14, "normal"),
    "section": ("Segoe UI", 18, "semibold"),
    "body": ("Segoe UI", 14, "normal"),
    "caption": ("Segoe UI", 12, "normal"),
}
