from ...asset import AssetController

from PySide6.QtGui import QColor, QFont

"""
styling configuration for interface components including colors, fonts, animations, and layout parameters
"""

ICON_ASSETS = AssetController("images/icons")
"""asset controller for loading icon images"""

# ANIMATION STYLING
ANIMATION_OPACITY_DURATION = 200
"""duration in milliseconds for opacity fade animations"""

# COLOR STYLING
BACKGROUND_COLOR = QColor(255, 255, 224, 255)
"""background color for interface elements"""

BORDER_COLOR = QColor(200, 200, 200, 255)
"""border color for interface elements"""

TEXT_COLOR = QColor(34, 34, 34, 255)
"""default text color"""

INFO_ACCENT = QColor(80, 140, 255, 255)
"""accent color for informational elements"""

ACTION_ACCENT = QColor(70, 180, 120, 255)
"""accent color for action elements"""

ERROR_ACCENT = QColor(220, 70, 70, 255)
"""accent color for error elements"""

# TEXT STYLING
FONT_NAME = "Comic Sans MS"
"""font family used for all text"""

HEADING_FONT = QFont(FONT_NAME, 16, QFont.Weight.Bold)
"""font for headings"""

SUBHEADING_FONT = QFont(FONT_NAME, 10, QFont.Weight.Light)
"""font for subheadings"""

DEFAULT_FONT = QFont(FONT_NAME, 12)
"""default font for regular text"""

TINY_FONT = QFont(FONT_NAME, 8, QFont.Weight.ExtraLight)
"""font for tiny text"""

# LAYOUT STYLING
BORDER_MARGIN = 16
"""margin from screen borders for positioning"""

BORDER_RADIUS = 4
"""border radius for rounded elements"""

PADDING = 8
"""internal padding for elements"""

# MISC
CLOSE_STR = "✕"
"""symbol used for close buttons"""

# UTILITY FUNCTIONS
def asRGB(color: QColor) -> str:
    """
    convert a QColor to an rgba CSS string representation.

    :param color: The color to convert
    :type color: QColor
    :return: RGBA string in format "rgba(r, g, b, a)"
    :rtype: str
    """
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})"
