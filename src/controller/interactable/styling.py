from PySide6.QtGui import QColor, QFont

ANIMATION_OPACITY_DURATION = 200

BACKGROUND_COLOR = QColor(255, 255, 224, 255)
TEXT_COLOR = QColor(34, 34, 34, 255)

FONT_NAME = "Comic Sans MS"

HEADING_FONT = QFont(FONT_NAME, 16, QFont.Weight.Bold)
SUBHEADING_FONT = QFont(FONT_NAME, 10, QFont.Weight.Light)
DEFAULT_FONT = QFont(FONT_NAME, 12)

BORDER_RADIUS = 4
BORDER_MARGIN = 8
PADDING = 8

def asRGB(color: QColor) -> str:
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})"
