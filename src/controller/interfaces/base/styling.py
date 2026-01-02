from ...asset import AssetController

from PySide6.QtGui import QColor, QFont

ICON_ASSETS = AssetController("images/icons")

# ANIMATION STYLING
ANIMATION_OPACITY_DURATION = 200

# COLOR STYLING
BACKGROUND_COLOR = QColor(255, 255, 224, 255)
BORDER_COLOR = QColor(200, 200, 200, 255)
TEXT_COLOR = QColor(34, 34, 34, 255)

INFO_ACCENT = QColor(80, 140, 255, 255)
ACTION_ACCENT = QColor(70, 180, 120, 255)
ERROR_ACCENT = QColor(220, 70, 70, 255)

# TEXT STYLING
FONT_NAME = "Comic Sans MS"

HEADING_FONT = QFont(FONT_NAME, 16, QFont.Weight.Bold)
SUBHEADING_FONT = QFont(FONT_NAME, 10, QFont.Weight.Light)
DEFAULT_FONT = QFont(FONT_NAME, 12)
TINY_FONT = QFont(FONT_NAME, 8, QFont.Weight.ExtraLight)

# LAYOUT STYLING
BORDER_MARGIN = 16
BORDER_RADIUS = 4
PADDING = 8

# MISC
CLOSE_STR = "✕"

# UTILITY FUNCTIONS
def asRGB(color: QColor) -> str:
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})"
