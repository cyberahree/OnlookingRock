from ..styling import DEFAULT_FONT, CLOSE_STR
from .primitives import _RockWidgetMixin

from PySide6.QtWidgets import QPushButton, QWidget
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon

from typing import Callable, Optional
from dataclasses import dataclass

class RockButton(QPushButton, _RockWidgetMixin):
    def __init__(
        self,
        text: str = "",
        parent: Optional[QWidget] = None,
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
        variant: str = "ghost",
        iconSizePx: int = 16,
        fixedSizePx: Optional[int] = None,
        onClick: Optional[Callable[[], None]] = None,
    ):
        super().__init__(text, parent)
        self._setRole("button", variant)
        self.setFont(DEFAULT_FONT)
        self.setFocusPolicy(Qt.NoFocus)

        if type(icon) is str:
            icon = QIcon(icon)

        if type(icon) is QIcon:
            self.setIcon(icon)
            self.setIconSize(QSize(iconSizePx, iconSizePx))

        if fixedSizePx is not None:
            self.setFixedSize(int(fixedSizePx), int(fixedSizePx))

        if onClick is not None:
            self.clicked.connect(lambda _checked=False: onClick())

class CloseButton(RockButton):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        onClick: Optional[Callable[[], None]] = None,
    ):
        super().__init__(CLOSE_STR, parent, variant="ghost", onClick=onClick)
        self.setFixedSize(28, 28)
