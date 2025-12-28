from ..styling import (
    asRGB,
    BACKGROUND_COLOR,
    TEXT_COLOR,
    DEFAULT_FONT,
    BORDER_RADIUS,
    BORDER_MARGIN,
    PADDING,
    ANIMATION_OPACITY_DURATION,
)

from ..base import InterfaceComponent

from PySide6.QtCore import (
    Qt,
    QTimer,
    QPoint,
    QRect,
    QPropertyAnimation,
    QEasingCurve,
    Signal
)

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect
from PySide6.QtGui import QPainter, QPolygon

from typing import Callable, Optional, Sequence, Iterable

import random

CHARACTERS_PER_SECOND = (25, 45)
TAIL_SIZE = 12

def getIntersectingarea(
    rectA: QRect,
    rectB: QRect
) -> int:
    intersction = rectA.intersected(rectB)

    if intersction.isNull():
        return 0
    
    return max(0, intersction.width()) * max(0, intersction.height())

class SpeechBubbleComponent(InterfaceComponent):
    typingFinished = Signal()
    fadeOutFinished = Signal()

    def __init__(
        self,
        sprite: QWidget,
        refreshRate: int = 5,
        blipSound: Optional[Callable[[], None]] = None,
        occludersProvider: Optional[Callable[[], Iterable[QWidget]]] = (lambda: []),
        keepOccludorsOnTop: bool = True
    ):
        super().__init__(sprite, refreshRate)

        self.sprite = sprite
        self.blip = blipSound or (lambda: None)
        self.refreshRate = refreshRate

        self.occludersProvider = occludersProvider
        self.keepOccludersOnTop = keepOccludorsOnTop

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

        self.opacityFx = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacityFx)
        self.opacityFx.setOpacity(0.0)

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

        # follow timer
        self.followTimer = QTimer(self)
        self.followTimer.timeout.connect(self._reposition)
        self.followTimer.start(max(1, 1000 // self.refreshRate))

        # movement animation
        self.moveAnim = QPropertyAnimation(self, b"pos")
        self.moveAnim.setEasingCurve(QEasingCurve.OutCubic)

        # fade animation
        self.fadeAnim = QPropertyAnimation(self.opacityFx, b"opacity")
        self.fadeAnim.setEasingCurve(QEasingCurve.OutCubic)
        self.fadeAnim.setDuration(ANIMATION_OPACITY_DURATION)
        self.fadeAnim.finished.connect(self._onFadeFinished)

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
        
        if typingDelay is not None:
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
        self._restackOccluders()

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
    
    def fadeIn(self):
        self.fadeAnim.stop()
        self.opacityFx.setOpacity(self.opacityFx.opacity())
        self.fadeAnim.setStartValue(self.opacityFx.opacity())
        self.fadeAnim.setEndValue(1.0)
        self.fadeAnim.start()
        if self.isHidden():
            self.show()
    
    def fadeOut(self):
        self.fadeAnim.stop()
        self.fadeAnim.setStartValue(self.opacityFx.opacity())
        self.fadeAnim.setEndValue(0.0)
        self.fadeAnim.start()
    
    def shutdown(self):
        self.isShuttingDown = True
        self.followTimer.stop()
        self.typeTimer.stop()
        self.fadeAnim.stop()
        self.moveAnim.stop()
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

        chracter = self.fullText[self.currentCharacterIndex - 1:self.currentCharacterIndex]

        if chracter.isalnum():
            self.blip()
    
    # fade animation handler
    def _onFadeFinished(self):
        if self.opacityFx.opacity() > 0.001:
            return
        
        self.hide()
        self.fadeOutFinished.emit()
    
    # repositioning
    def _clampToScreen(
        self,
        x: int, y: int,
        width: int, height: int,
        screen: QRect
    ) -> QPoint:
        x = max(screen.left() + BORDER_MARGIN, min(x, screen.right() - width - BORDER_MARGIN))
        y = max(screen.top() + BORDER_MARGIN, min(y, screen.bottom() - height - BORDER_MARGIN))

        return QPoint(x, y)

    def _score(
        self,
        bounds: QRect,
        preferredTopLeft: QPoint,
        occluders: Sequence[QRect]
    ) -> tuple[int, int]:
        overlap = sum(getIntersectingarea(bounds, o) for o in occluders)
        dist = (bounds.topLeft() - preferredTopLeft).manhattanLength()
        return (overlap, dist)

    def _bestCandidate(
        self,
        preferred: QPoint,
        alt: QPoint,
        width: int,
        height: int,
        screen: QRect,
        occluders: Sequence[QRect],
    ) -> QPoint:
        candidates: list[QPoint] = []

        def addBaseAndNudges(base: QPoint):
            candidates.append(base)
            base_rect = QRect(base.x(), base.y(), width, height)

            for o in occluders:
                if not base_rect.intersects(o):
                    continue

                candidates.append(QPoint(base.x(), o.top() - height - BORDER_MARGIN))
                candidates.append(QPoint(base.x(), o.bottom() + BORDER_MARGIN))

        addBaseAndNudges(preferred)
        addBaseAndNudges(alt)

        bestPosition = None
        bestScore = None

        for candidatePosition in candidates:
            p2 = self._clampToScreen(candidatePosition.x(), candidatePosition.y(), width, height, screen)
            r = QRect(p2.x(), p2.y(), width, height)
            s = self._score(r, preferred, occluders)

            if bestScore is None or s < bestScore:
                bestScore = s
                bestPosition = p2

                # no more overlap is possible
                if s[0] == 0:
                    break

        return bestPosition or preferred

    def _reposition(self, force_show: bool = False):
        if not self.sprite:
            return

        if self.isHidden() and not force_show:
            return

        if force_show:
            self.show()

        screen = self.sprite.screen().availableGeometry()
        sprite_rect = self.sprite.frameGeometry()
        width, height = self.width(), self.height()

        # prefer right side, fallback left
        preferred_x = sprite_rect.right() + BORDER_MARGIN
        alt_x = sprite_rect.left() - width - BORDER_MARGIN

        # anchor around sprite center (not sprite.top())
        base_y = sprite_rect.center().y() - (height // 2)

        preferred = QPoint(preferred_x, base_y)
        alt = QPoint(alt_x, base_y)

        occluders = list(self._iterateOccludersBounds())
        target = self._bestCandidate(preferred, alt, width, height, screen, occluders)

        # tail direction
        prev_tail = self.tailDirection

        bubble_center_x = target.x() + (width // 2)
        sprite_center_x = sprite_rect.center().x()

        self.tailDirection = "left" if sprite_center_x < bubble_center_x else "right"

        if prev_tail != self.tailDirection:
            self.update()

        self._animateTo(target)

    def _animateTo(self, target: QPoint):
        if (self.pos() - target).manhattanLength() < 2:
            self.move(target)
            return

        if self.moveAnim.state() == QPropertyAnimation.Running:
            self.moveAnim.stop()

        distance = (self.pos() - target).manhattanLength()

        self.moveAnim.setDuration(min(300, max(80, distance)))
        self.moveAnim.setStartValue(self.pos())
        self.moveAnim.setEndValue(target)
        self.moveAnim.start()
    
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
