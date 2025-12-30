from ..styling import PADDING

from PySide6.QtWidgets import (
    QFrame,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from typing import Optional

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
