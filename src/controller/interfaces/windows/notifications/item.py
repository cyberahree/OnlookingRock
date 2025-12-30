from ...base.animation import FadeableMixin
from ...base.lookskit import BodyLabel, HeadingLabel, RockButton, applyRockStyle

from ...base.styling import (
    ACTION_ACCENT,
    ANIMATION_OPACITY_DURATION,
    BACKGROUND_COLOR,
    BORDER_COLOR,
    BORDER_RADIUS,
    DEFAULT_FONT,
    ERROR_ACCENT,
    HEADING_FONT,
    INFO_ACCENT,
    PADDING,
    TINY_FONT,
    asRGB,
)

from PySide6.QtCore import Qt, QTimer, Signal

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from typing import Callable, List, Optional, Sequence
from dataclasses import dataclass

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

        self.setFont(DEFAULT_FONT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.initFadeable(durationMs=ANIMATION_OPACITY_DURATION)

        self.outerLayout = QVBoxLayout(self)
        self.outerLayout.setContentsMargins(PADDING, PADDING, PADDING, PADDING)
        self.outerLayout.setSpacing(PADDING // 2)

        self.headerLayout = QHBoxLayout()
        self.headerLayout.setContentsMargins(0, 0, 0, 0)
        self.headerLayout.setSpacing(PADDING // 2)

        self.callerLabel = HeadingLabel(kind, self)
        self.callerLabel.setObjectName("tinyLabel")
        self.callerLabel.setFont(TINY_FONT)

        self.titleLabel = HeadingLabel(title, self)
        self.titleLabel.setObjectName("toastTitle")

        self.closeButton = RockButton("x", self, variant="ghost", onClick=self.dismissToast)
        self.closeButton.setObjectName("toastCloseButton")
        self.closeButton.setFont(HEADING_FONT)
        self.closeButton.setFixedSize(24, 24)

        self.headerLayout.addWidget(self.titleLabel)
        self.headerLayout.addWidget(self.closeButton)

        self.bodyLabel = BodyLabel(message, self, wrap=True, selectable=True)
        self.bodyLabel.setObjectName("toastBody")

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

        self.outerLayout.addWidget(self.callerLabel)
        self.outerLayout.addLayout(self.headerLayout)
        self.outerLayout.addWidget(self.bodyLabel)

        if self.actionButtons:
            self.outerLayout.addLayout(self.actionsLayout)

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
            QFrame#toastItem {{
                background-color: {asRGB(BACKGROUND_COLOR)};
                border: 2px solid {asRGB(BORDER_COLOR)};
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
