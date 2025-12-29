from ..styling import (
    asRGB,
    BACKGROUND_COLOR,
    TEXT_COLOR,
    DEFAULT_FONT,
    BORDER_RADIUS,
    BORDER_MARGIN,
    PADDING,
)

from ..positioning import bestCandidate
from ..base import InterfaceComponent
from ..mixin import SpriteAnchorMixin

from PySide6.QtCore import (
    Qt,
    QTimer,
    QPoint,
    QRect,
    Signal
)

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect
from PySide6.QtGui import QPainter, QPolygon

from typing import Callable, Optional, Sequence, Iterable

import random

CHARACTERS_PER_SECOND = (25, 45)
TAIL_SIZE = 12

class SpeechBubbleComponent(InterfaceComponent, SpriteAnchorMixin):
    typingFinished = Signal()
    fadeOutFinished = Signal()

    def __init__(
        self,
        sprite: QWidget,
        refreshRate: int = 5,
        blipSound: Optional[Callable[[], None]] = None,
        occludersProvider: Optional[Callable[[], Iterable[QWidget]]] = (lambda: []),
        keepOccludersOnTop: bool = True
    ):
        super().__init__(sprite, refreshRate)

        self.sprite = sprite
        self.blip = blipSound or (lambda: None)
        self.refreshRate = refreshRate

        self.occludersProvider = occludersProvider
        self.keepOccludersOnTop = keepOccludersOnTop

        self.isShuttingDown = False
        self.tailDirection = "right"

        # typing state
        self.fullText = ""
        self.currentCharacterIndex = 0
        self.currentTypingDelay = CHARACTERS_PER_SECOND[0]

        # window setup
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.NoFocus)

        self.setOpacity(0.0)
        self.fadeFinished.connect(self._handleFadeFinished)

        # label
        self.label = QLabel("")
        self.label.setWordWrap(True)
        self.label.setMaximumWidth(220)
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label.setFont(DEFAULT_FONT)
        self.label.setStyleSheet(f"""
            QLabel {{
                background-color: {asRGB(BACKGROUND_COLOR)};
                color: {asRGB(TEXT_COLOR)};
                padding: {PADDING}px;
                border-radius: {BORDER_RADIUS}px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, TAIL_SIZE)
        layout.addWidget(self.label)

        # typing timer
        self.typeTimer = QTimer(self)
        self.typeTimer.timeout.connect(self._typeNextCharacter)

        self.followTimer.start()

        self.hide()

    # occluders
    def setOccludersProvider(self, provider: Callable[[], Sequence[QWidget]]):
        self.occludersProvider = provider or (lambda: [])

    def getOccluderWidgets(self) -> Sequence[QWidget]:
        try:
            return list(self.occludersProvider()) or []
        except Exception:
            return []

    def _iterateOccludersBounds(self) -> Iterable[QRect]:
        for widget in self.getOccluderWidgets():
            if not widget or not widget.isVisible():
                continue

            yield widget.frameGeometry()
    
    def _restackOccluders(self) -> None:
        if not self.keepOccludersOnTop:
            return
        
        for widget in self.getOccluderWidgets():
            if (not widget or not widget.isVisible()):
                continue

            widget.raise_()
    
    # input handlers
    def mousePressEvent(self, event):
        if self.typeTimer.isActive():
            # TODO: do this
            self.skipTyping()
    
    # interface methods
    def startTyping(self, text: str, typingDelay: Optional[int] = None):
        if self.isShuttingDown:
            return
        
        if typingDelay is None:
            typingDelay = random.randint(
                CHARACTERS_PER_SECOND[0],
                CHARACTERS_PER_SECOND[1]
            )

        self.fullText = text
        self.currentCharacterIndex = 0
        self.currentTypingDelay = typingDelay

        self.label.setText("")
        self.adjustSize()
        self._reposition(force_show=True)

        self.fadeIn()
        self.raise_()
        self.followTimer.start()
        self.restackOccluders()

        self.typeTimer.start(self.currentTypingDelay)
    
    def skipTyping(self):
        if not self.typeTimer.isActive():
            return

        self.stopTyping(
            showFullText=True
        )
        
    def stopTyping(
        self,
        showFullText: bool = False
    ):
        if not self.typeTimer.isActive():
            return

        self.typeTimer.stop()

        if showFullText:
            self.label.setText(self.fullText)
            self.adjustSize()
    
    def shutdown(self):
        self.isShuttingDown = True
        self.followTimer.stop()
        self.typeTimer.stop()
        self.fadeAnimation.stop()
        self.moveAnimation.stop()
        self.hide()
    
    # internal methods
    def _typeNextCharacter(self):
        if self.isShuttingDown:
            self.typeTimer.stop()
            return

        if self.currentCharacterIndex >= len(self.fullText):
            self.typeTimer.stop()
            self.typingFinished.emit()
            return

        self.currentCharacterIndex += 1
        self.label.setText(self.fullText[:self.currentCharacterIndex])
        self.adjustSize()
        self._reposition()

        character = self.fullText[self.currentCharacterIndex - 1:self.currentCharacterIndex]

        if character.isalnum():
            self.blip()
    
    # fade animation handler
    def _handleFadeFinished(self, endOpacity: float) -> None:
        if endOpacity <= 0.001:
            self.fadeOutFinished.emit()
    
    def _reposition(self, forceShow: bool = False) -> None:
        if not self.sprite:
            return

        if self.isHidden() and not forceShow:
            return

        if forceShow:
            self.show()

        target = self.anchorNextToSprite(
            yAlign="center",
            preferredSide="right",
            margin=BORDER_MARGIN,
        )

        # tail direction (point inwards toward the sprite)
        prev_tail = self.tailDirection
        self.tailDirection = self.inwardHorizontalDirection(target)

        if prev_tail != self.tailDirection:
            self.update()

        self.animateTo(target)
            
    # tail painting
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(BACKGROUND_COLOR)
        painter.setPen(Qt.NoPen)

        label_rect = self.label.geometry()
        base_x = label_rect.center().x()
        base_y = label_rect.bottom()

        if self.tailDirection == "left":
            tip = QPoint(base_x - TAIL_SIZE, base_y + TAIL_SIZE)
        else:
            tip = QPoint(base_x + TAIL_SIZE, base_y + TAIL_SIZE)

        left = QPoint(base_x - TAIL_SIZE // 2, base_y)
        right = QPoint(base_x + TAIL_SIZE // 2, base_y)
        painter.drawPolygon(QPolygon([left, tip, right]))
