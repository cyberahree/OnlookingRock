from ..styling import DEFAULT_FONT, HEADING_FONT, SUBHEADING_FONT
from .primitives import _RockWidgetMixin

from PySide6.QtWidgets import QLabel, QWidget
from PySide6.QtCore import Qt

from typing import Optional

class HeadingLabel(QLabel, _RockWidgetMixin):
    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self._setRole("heading")
        self.setFont(HEADING_FONT)
        self.setWordWrap(True)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)

class SubheadingLabel(QLabel, _RockWidgetMixin):
    def __init__(
        self,
        text: str = "",
        parent: Optional[QWidget] = None,
        selectable: bool = False,
    ):
        super().__init__(text, parent)
        self._setRole("subheading")
        self.setFont(SUBHEADING_FONT)
        self.setWordWrap(True)

        if selectable:
            self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        else:
            self.setTextInteractionFlags(Qt.NoTextInteraction)

class BodyLabel(QLabel, _RockWidgetMixin):
    def __init__(
        self,
        text: str = "",
        parent: Optional[QWidget] = None,
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
        wrap: bool = True,
        selectable: bool = True,
    ):
        super().__init__(text, parent)
        self._setRole("muted")
        self.setFont(DEFAULT_FONT)
        self.setWordWrap(bool(wrap))

        if selectable:
            self.setTextInteractionFlags(Qt.TextSelectableByMouse)
