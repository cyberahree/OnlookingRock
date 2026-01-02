from ..styling import DEFAULT_FONT
from .primitives import _RockWidgetMixin

from PySide6.QtWidgets import QComboBox, QWidget
from PySide6.QtCore import Qt

from typing import Callable, List, Optional
from dataclasses import dataclass

@dataclass
class DropdownSpec:
    items: List[str]
    variant: str = "default"
    onValueChanged: Optional[Callable[[str], None]] = None

class RockDropdown(QComboBox, _RockWidgetMixin):
    def __init__(
        self,
        items: Optional[List[str]] = None,
        parent: Optional[QWidget] = None,
        *,
        variant: str = "default",
        onValueChanged: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(parent)

        self._setRole("dropdown", variant)
        self.setFont(DEFAULT_FONT)
        self.setFocusPolicy(Qt.NoFocus)

        if items is None:
            items = []

        if items:
            self.addItems(items)

        if onValueChanged is not None:
            self.currentTextChanged.connect(onValueChanged)

    def addItem(self, item: str) -> None:
        super().addItem(item)
