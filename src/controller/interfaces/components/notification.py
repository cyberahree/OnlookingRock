from ..base.styling import (
    asRGB,
    BACKGROUND_COLOR,
    BORDER_COLOR,
    HEADING_FONT,
    DEFAULT_FONT,
    BORDER_RADIUS,
    BORDER_MARGIN,
    PADDING,
    ANIMATION_OPACITY_DURATION,
    INFO_ACCENT,
    ACTION_ACCENT,
    ERROR_ACCENT
)

from ..base.uikit import applyRockStyle, RockButton, HeadingLabel, BodyLabel

from ..mixin import FadeableMixin, PrimaryScreenAnchorMixin
from ..base import InterfaceComponent

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget
)

from PySide6.QtCore import Qt, QTimer, Signal

from typing import Callable, Optional, Sequence, List
from dataclasses import dataclass

SIZE_CONSTRAINTS = (256, 600)

@dataclass
class PopupAction:
    label: str
    callback: Callable[[], None]
    dismiss: bool = True

class ToastItem(QFrame, FadeableMixin):
    dismissed = Signal(object)

    def __init__(
        self,
        kind: str,
        title: str,
        message: str,
        actions: Sequence[PopupAction] = (),
        timeoutMs: Optional[int] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.kind = (kind or "info").lower().strip()
        self.timeoutMs = timeoutMs
        self.isClosed = False

        self.setObjectName("toastItem")
        self.setProperty("kind", self.kind)
        self.setProperty("rockRole", "container")
        self.setProperty("variant", "card")

        # visuals
        self.setFont(DEFAULT_FONT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.initFadeable(durationMs=ANIMATION_OPACITY_DURATION)

        # main layout
        self.outerLayout = QVBoxLayout(self)
        self.outerLayout.setContentsMargins(PADDING, PADDING, PADDING, PADDING)
        self.outerLayout.setSpacing(PADDING // 2)

        # top row
        self.headerLayout = QHBoxLayout()
        self.headerLayout.setContentsMargins(0, 0, 0, 0)
        self.headerLayout.setSpacing(PADDING // 2)

        self.titleLabel = HeadingLabel(title, self)
        self.titleLabel.setObjectName("toastTitle")

        self.closeButton = RockButton("x", self, variant="ghost", onClick=self.dismissToast)
        self.closeButton.setObjectName("toastCloseButton")
        self.closeButton.setFont(HEADING_FONT)
        self.closeButton.setFixedSize(24, 24)
        
        self.headerLayout.addWidget(self.titleLabel)
        self.headerLayout.addWidget(self.closeButton)

        # body
        self.bodyLabel = BodyLabel(message, self, wrap=True, selectable=True)
        self.bodyLabel.setObjectName("toastBody")

        # actions
        self.actionsLayout = QHBoxLayout()
        self.actionsLayout.setContentsMargins(0, 0, 0, 0)
        self.actionsLayout.setSpacing(PADDING // 2)
        self.actionsLayout.addStretch(1)

        self.actionButtons: List[QPushButton] = []

        for action in actions or ():
            button = RockButton(
                action.label,
                self,
                variant="surface",
                onClick=lambda a=action: self._handleActionClicked(a),
            )
            button.setObjectName("toastActionButton")

            self.actionButtons.append(button)
            self.actionsLayout.addWidget(button)

        # apply
        self.outerLayout.addLayout(self.headerLayout)
        self.outerLayout.addWidget(self.bodyLabel)
        
        if self.actionButtons:
            self.outerLayout.addLayout(self.actionsLayout)

        # auto-dismiss
        self.timeoutTimer = QTimer(self)
        self.timeoutTimer.setSingleShot(True)
        self.timeoutTimer.timeout.connect(self.dismissToast)

        if (self.timeoutMs is not None) and self.timeoutMs > 0:
            self.timeoutTimer.start(self.timeoutMs)
        
        self.applyStyleSheet()
    
    def applyStyleSheet(self) -> None:
        applyRockStyle(
            self,
            extraQss=f"""
            /* Toast-specific chrome + kind accents */
            QFrame#toastItem {{
                background-color: {asRGB(BACKGROUND_COLOR)};
                border: 1px solid {asRGB(BORDER_COLOR)};
                border-radius: {BORDER_RADIUS}px;
            }}

            QFrame#toastItem[kind=\"info\"] {{
                border: 2px solid {asRGB(INFO_ACCENT)};
            }}

            QFrame#toastItem[kind=\"action\"] {{
                background-color: {asRGB(BACKGROUND_COLOR.lighter(110))};
                border: 2px solid {asRGB(ACTION_ACCENT)};
            }}

            QFrame#toastItem[kind=\"error\"] {{
                background-color: {asRGB(BACKGROUND_COLOR.lighter(120))};
                border: 2px solid {asRGB(ERROR_ACCENT)};
            }}
            """,
        )
    
    def _handleActionClicked(self, action: PopupAction) -> None:
        if self.isClosed:
            return
        
        try:
            action.callback()
        except Exception:
            pass

        if action.dismiss:
            self.dismissToast()
        
    def dismissToast(self) -> None:
        if self.isClosed:
            return
        
        self.isClosed = True
        self.timeoutTimer.stop()

        self.fadeOut()

    def onFadeFinished(self, endOpacity: float) -> None:
        if endOpacity <= 0.001:
            self.dismissed.emit(self)

class ToastStackComponent(InterfaceComponent, PrimaryScreenAnchorMixin):
    def __init__(
        self,
        sprite: QWidget,
        refreshRate: int = 10,
        widthPx: int = SIZE_CONSTRAINTS[0],
        maxVisible: int = 5,
    ) -> None:
        super().__init__(sprite, refreshRate)

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
