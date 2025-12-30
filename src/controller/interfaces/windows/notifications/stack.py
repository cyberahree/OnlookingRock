from .item import PopupAction, ToastItem

from ...base.anchor import PrimaryScreenAnchorMixin
from ...base.styling import BORDER_MARGIN, PADDING
from ...base import InterfaceComponent

from PySide6.QtWidgets import QVBoxLayout, QWidget
from PySide6.QtCore import Qt

from typing import List, Optional, Sequence

SIZE_CONSTRAINTS = (256, 600)

class ToastStackComponent(InterfaceComponent, PrimaryScreenAnchorMixin):
    def __init__(
        self,
        sprite: QWidget,
        clock,
        widthPx: int = SIZE_CONSTRAINTS[0],
        maxVisible: int = 5,
    ) -> None:
        super().__init__(sprite, clock)

        self.widthPx = int(max(SIZE_CONSTRAINTS[0], widthPx))
        self.maxVisible = int(max(1, maxVisible))

        self.setWindowFlags(
            Qt.Tool |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.NoFocus)

        self.setObjectName("toastStack")
        self.setFixedWidth(self.widthPx)

        self.toastItems: List[ToastItem] = []

        self.outerLayout = QVBoxLayout(self)
        self.outerLayout.setContentsMargins(0, 0, 0, 0)
        self.outerLayout.setSpacing(PADDING // 2)

        self.outerLayout.addStretch(1)

        self.fadeOnOpen = False
        self.fadeOnClose = False

        self.hide()

    def post(
        self,
        kind: str,
        title: str,
        message: str,
        actions: Sequence[PopupAction] = (),
        timeoutMs: Optional[int] = None,
    ) -> ToastItem:
        if timeoutMs is None:
            timeoutMs = 4500 if not actions else 0

        item = ToastItem(
            kind=kind,
            title=title,
            message=message,
            actions=actions,
            timeoutMs=timeoutMs,
            parent=self,
        )

        item.dismissed.connect(self.onItemDismissed)

        while len(self.toastItems) >= self.maxVisible:
            oldest = self.toastItems.pop(0)
            oldest.dismissed.disconnect(self.onItemDismissed)

            self.outerLayout.removeWidget(oldest)
            oldest.deleteLater()

        self.toastItems.append(item)
        self.outerLayout.addWidget(item)

        if self.isHidden():
            self.open()
        else:
            self.raise_()

        if self.sprite:
            self.sprite.raise_()

        self.updateGeometry()
        return item

    def clear(self) -> None:
        for item in list(self.toastItems):
            item.dismissToast()

    def onItemDismissed(self, item: ToastItem) -> None:
        if item in self.toastItems:
            self.toastItems.remove(item)

        self.outerLayout.removeWidget(item)
        item.deleteLater()

        self.updateGeometry()

        if not self.toastItems:
            self.hide()
            self.followTimer.stop()

    def updateGeometry(self) -> None:
        self.adjustSize()
        self._reposition()

    def _reposition(self) -> None:
        self.animateTo(
            self.anchorBottomRight(margin=BORDER_MARGIN)
        )

