"""
ui building blocks for interfaces

visual keys pulled from .styling, and styled via shared QSS

example use:
    from ..components.uikit import (
        applyRockStyle,
        SurfaceFrame,
        HeadingLabel, BodyLabel,
        RockButton,
    )

    class MyComponent(InterfaceComponent):
        def build(self):
            root = SurfaceFrame(self)
            outer = QVBoxLayout(self)
            outer.setContentsMargins(0, 0, 0, 0)
            outer.addWidget(root)

            root.contentLayout.addWidget(HeadingLabel("Title"))
            root.contentLayout.addWidget(BodyLabel("Hello"))
            root.contentLayout.addWidget(RockButton("OK", variant="primary"))

            applyRockStyle(self)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Callable

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .styling import (
    asRGB,
    BACKGROUND_COLOR,
    BORDER_COLOR,
    TEXT_COLOR,
    HEADING_FONT,
    SUBHEADING_FONT,
    DEFAULT_FONT,
    BORDER_RADIUS,
    PADDING,
    INFO_ACCENT,
    ACTION_ACCENT,
    ERROR_ACCENT,
)

# shared/cached QSS
_CACHED_QSS: Optional[str] = None

def _rgba(color: QColor, alpha: Optional[int] = None) -> str:
    if alpha is None:
        return asRGB(color)

    c = QColor(color)
    c.setAlpha(int(max(0, min(255, alpha))))
    return asRGB(c)

def _build_base_qss() -> str:
    # derived colors
    hover_surface = QColor(BACKGROUND_COLOR).darker(106)
    pressed_surface = QColor(BACKGROUND_COLOR).darker(112)

    # button fills
    primary_fill = QColor(ACTION_ACCENT)
    primary_hover = QColor(ACTION_ACCENT).lighter(112)
    primary_pressed = QColor(ACTION_ACCENT).darker(112)

    info_fill = QColor(INFO_ACCENT)
    info_hover = QColor(INFO_ACCENT).lighter(112)
    info_pressed = QColor(INFO_ACCENT).darker(112)

    danger_fill = QColor(ERROR_ACCENT)
    danger_hover = QColor(ERROR_ACCENT).lighter(112)
    danger_pressed = QColor(ERROR_ACCENT).darker(112)

    return f"""
    /* Containers */
    QFrame[rockRole="container"] {{
        background-color: {_rgba(BACKGROUND_COLOR)};
        border: 1px solid {_rgba(BORDER_COLOR)};
        border-radius: {BORDER_RADIUS}px;
    }}

    QFrame[rockRole="container"][variant="surface"] {{
        border: none;
    }}

    QFrame[rockRole="container"][variant="card"] {{
        border: 1px solid {_rgba(BORDER_COLOR)};
    }}

    QFrame[rockRole="container"][variant="inset"] {{
        background-color: {_rgba(QColor(BACKGROUND_COLOR).darker(104))};
        border: 1px solid {_rgba(QColor(BORDER_COLOR).darker(106))};
    }}

    QFrame[rockRole="container"][variant="ghost"] {{
        background: transparent;
        border: none;
    }}

    /* Text */
    QLabel[rockRole="heading"],
    QLabel[rockRole="subheading"],
    QLabel[rockRole="text"],
    QLabel[rockRole="muted"] {{
        color: {_rgba(TEXT_COLOR)};
    }}

    QLabel[rockRole="muted"] {{
        color: rgba({TEXT_COLOR.red()}, {TEXT_COLOR.green()}, {TEXT_COLOR.blue()}, 170);
    }}

    /* Buttons */
    QPushButton[rockRole="button"] {{
        color: {_rgba(TEXT_COLOR)};
        background-color: rgba(255, 255, 255, 120);
        border: 1px solid rgba(0, 0, 0, 35);
        border-radius: {BORDER_RADIUS}px;
        padding: 4px 10px;
        outline: none;
    }}

    QPushButton[rockRole="button"]:hover {{
        background-color: rgba(255, 255, 255, 180);
    }}

    QPushButton[rockRole="button"]:pressed {{
        background-color: rgba(0, 0, 0, 18);
    }}

    QPushButton[rockRole="button"][variant="ghost"] {{
        background: transparent;
        border: none;
        padding: 2px 6px;
    }}

    QPushButton[rockRole="button"][variant="ghost"]:hover {{
        background-color: rgba(0, 0, 0, 18);
    }}

    QPushButton[rockRole="button"][variant="ghost"]:pressed {{
        background-color: rgba(0, 0, 0, 28);
    }}

    QPushButton[rockRole="button"][variant="surface"] {{
        background-color: {_rgba(BACKGROUND_COLOR)};
        border: 1px solid {_rgba(BORDER_COLOR)};
    }}

    QPushButton[rockRole="button"][variant="surface"]:hover {{
        background-color: {_rgba(hover_surface)};
    }}

    QPushButton[rockRole="button"][variant="surface"]:pressed {{
        background-color: {_rgba(pressed_surface)};
    }}

    QPushButton[rockRole="button"][variant="primary"] {{
        background-color: {_rgba(primary_fill, 230)};
        border: 1px solid {_rgba(primary_fill.darker(120))};
    }}

    QPushButton[rockRole="button"][variant="primary"]:hover {{
        background-color: {_rgba(primary_hover, 235)};
    }}

    QPushButton[rockRole="button"][variant="primary"]:pressed {{
        background-color: {_rgba(primary_pressed, 235)};
    }}

    QPushButton[rockRole="button"][variant="info"] {{
        background-color: {_rgba(info_fill, 230)};
        border: 1px solid {_rgba(info_fill.darker(120))};
    }}

    QPushButton[rockRole="button"][variant="info"]:hover {{
        background-color: {_rgba(info_hover, 235)};
    }}

    QPushButton[rockRole="button"][variant="info"]:pressed {{
        background-color: {_rgba(info_pressed, 235)};
    }}

    QPushButton[rockRole="button"][variant="danger"] {{
        background-color: {_rgba(danger_fill, 225)};
        border: 1px solid {_rgba(danger_fill.darker(120))};
    }}

    QPushButton[rockRole="button"][variant="danger"]:hover {{
        background-color: {_rgba(danger_hover, 235)};
    }}

    QPushButton[rockRole="button"][variant="danger"]:pressed {{
        background-color: {_rgba(danger_pressed, 235)};
    }}

    /* Simple divider */
    QFrame[rockRole="divider"] {{
        background-color: rgba(0, 0, 0, 35);
        min-height: 1px;
        max-height: 1px;
    }}
    """.strip()

def rockStylesheet() -> str:
    """Return the shared QSS (cached)."""
    global _CACHED_QSS

    if _CACHED_QSS is None:
        _CACHED_QSS = _build_base_qss()

    return _CACHED_QSS

def applyRockStyle(root: QWidget, extraQss: str = "") -> None:
    """Apply shared style + optional extra QSS onto a root widget."""
    base = rockStylesheet()

    if extraQss:
        root.setStyleSheet(base + "\n\n" + extraQss)
    else:
        root.setStyleSheet(base)

# component widgets
class _RockWidgetMixin:
    def _setRole(self, role: str, variant: Optional[str] = None) -> None:
        self.setProperty("rockRole", role)

        if variant is not None:
            self.setProperty("variant", variant)

class SurfaceFrame(QFrame, _RockWidgetMixin):
    def __init__(self, parent: Optional[QWidget] = None, *, padding: int = PADDING):
        super().__init__(parent)
        self._setRole("container", "surface")
        self.setFrameShape(QFrame.NoFrame)

        self.contentLayout = QVBoxLayout(self)
        self.contentLayout.setContentsMargins(padding, padding, padding, padding)
        self.contentLayout.setSpacing(max(0, padding // 2))

class CardFrame(QFrame, _RockWidgetMixin):
    def __init__(self, parent: Optional[QWidget] = None, *, padding: int = PADDING):
        super().__init__(parent)
        self._setRole("container", "card")
        self.setFrameShape(QFrame.NoFrame)

        self.contentLayout = QVBoxLayout(self)
        self.contentLayout.setContentsMargins(padding, padding, padding, padding)
        self.contentLayout.setSpacing(max(0, padding // 2))

class InsetFrame(QFrame, _RockWidgetMixin):
    def __init__(self, parent: Optional[QWidget] = None, *, padding: int = PADDING):
        super().__init__(parent)
        self._setRole("container", "inset")
        self.setFrameShape(QFrame.NoFrame)

        self.contentLayout = QVBoxLayout(self)
        self.contentLayout.setContentsMargins(padding, padding, padding, padding)
        self.contentLayout.setSpacing(max(0, padding // 2))

class Divider(QFrame, _RockWidgetMixin):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setRole("divider")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFrameShape(QFrame.NoFrame)

class HeadingLabel(QLabel, _RockWidgetMixin):
    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self._setRole("heading")
        self.setFont(HEADING_FONT)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)

class SubheadingLabel(QLabel, _RockWidgetMixin):
    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self._setRole("subheading")
        self.setFont(SUBHEADING_FONT)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)

class BodyLabel(QLabel, _RockWidgetMixin):
    def __init__(
        self,
        text: str = "",
        parent: Optional[QWidget] = None,
        *,
        wrap: bool = True,
        selectable: bool = True,
    ):
        super().__init__(text, parent)
        self._setRole("text")
        self.setFont(DEFAULT_FONT)
        self.setWordWrap(bool(wrap))

        if selectable:
            self.setTextInteractionFlags(Qt.TextSelectableByMouse)

class MutedLabel(QLabel, _RockWidgetMixin):
    def __init__(
        self,
        text: str = "",
        parent: Optional[QWidget] = None,
        *,
        wrap: bool = True,
        selectable: bool = True,
    ):
        super().__init__(text, parent)
        self._setRole("muted")
        self.setFont(DEFAULT_FONT)
        self.setWordWrap(bool(wrap))

        if selectable:
            self.setTextInteractionFlags(Qt.TextSelectableByMouse)

class RockButton(QPushButton, _RockWidgetMixin):
    def __init__(
        self,
        text: str = "",
        parent: Optional[QWidget] = None,
        *,
        variant: str = "default",
        onClick: Optional[Callable[[], None]] = None,
    ):
        super().__init__(text, parent)
        self._setRole("button", variant)
        self.setFont(DEFAULT_FONT)
        self.setFocusPolicy(Qt.NoFocus)

        if onClick is not None:
            self.clicked.connect(lambda _checked=False: onClick())

class RockIconButton(QPushButton, _RockWidgetMixin):
    def __init__(
        self,
        icon: Optional[QIcon] = None,
        text: str = "",
        parent: Optional[QWidget] = None,
        *,
        variant: str = "ghost",
        iconSizePx: int = 16,
        fixedSizePx: Optional[int] = None,
        onClick: Optional[Callable[[], None]] = None,
    ):
        super().__init__(text, parent)
        self._setRole("button", variant)
        self.setFont(DEFAULT_FONT)
        self.setFocusPolicy(Qt.NoFocus)

        if icon is not None:
            self.setIcon(icon)
            try:
                self.setIconSize(QSize(iconSizePx, iconSizePx))
            except Exception:
                # Qt.QSize exists on QtCore, but keep this resilient if API differs
                pass

        if fixedSizePx is not None:
            self.setFixedSize(int(fixedSizePx), int(fixedSizePx))

        if onClick is not None:
            self.clicked.connect(lambda _checked=False: onClick())

class ContentColumn(QVBoxLayout):
    def __init__(self, parent: Optional[QWidget] = None, *, spacing: Optional[int] = None):
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(PADDING // 2 if spacing is None else int(max(0, spacing)))

class ContentRow(QHBoxLayout):
    def __init__(self, parent: Optional[QWidget] = None, *, spacing: Optional[int] = None):
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(PADDING // 2 if spacing is None else int(max(0, spacing)))

@dataclass(frozen=True)
class ButtonSpec:
    text: str
    variant: str = "default"
    onClick: Optional[Callable[[], None]] = None
