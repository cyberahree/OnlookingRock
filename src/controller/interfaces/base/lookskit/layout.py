from ..styling import PADDING

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from typing import Optional

class ContentColumn(QVBoxLayout):
    def __init__(self, parent: Optional[QWidget] = None, *, spacing: Optional[int] = 0):
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)

        self.setSpacing(
            PADDING // 2 if spacing is None else int(max(0, spacing))
        )

class ContentRow(QHBoxLayout):
    def __init__(self, parent: Optional[QWidget] = None, *, spacing: Optional[int] = 0):
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)

        self.setSpacing(
            PADDING // 2 if spacing is None else int(max(0, spacing))
        )
