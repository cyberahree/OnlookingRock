from ..interfaces.styling import (
    asRGB,
    BACKGROUND_COLOR,
    TEXT_COLOR,
    DEFAULT_FONT,
    BORDER_RADIUS,
    BORDER_MARGIN,
    PADDING,
    ANIMATION_OPACITY_DURATION
)

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QPolygon

from ..interfaces.components.speechbubble import SpeechBubbleComponent

from dataclasses import dataclass
from collections import deque

import random

TAIL_WIDTH = 12

CHARACTERS_PER_SECOND = (25, 45)
READING_DELAY = 4500
READING_WPS = (180 / 60) # words per second

@dataclass
class SpeechItem:
    text: str
    duration: int
    typingDelayMs: int

class SpeechBubbleController(QWidget):
    def __init__(
        self,
        sprite: QWidget,
        refreshRate: int = 5,
        occludersProvider = None,
        **kwargs
    ):
        super().__init__()

        self.bubble = SpeechBubbleComponent(
            sprite,
            refreshRate,
            sprite.Sound.playSpeechBlip,
            occludersProvider=occludersProvider,
            **kwargs
        )

        self.queue = deque()
        self.active = False
        self.shuttingDown = False

        self._nextTimer = QTimer(self)
        self._nextTimer.setSingleShot(True)
        self._nextTimer.timeout.connect(self._showNext)

    def addSpeech(
        self,
        text: str,
        duration: int = None
    ):
        if self.shuttingDown:
            return
        
        typing_delay = (1000 // random.randint(*CHARACTERS_PER_SECOND))

        if duration is None:
            wordCount = len(text.split())
            characterCount = len(text)

            timeTyping = characterCount * typing_delay
            timeReading = (wordCount / READING_WPS) * 1000

            duration = max(timeTyping + timeReading + READING_DELAY, 3000)
    
        self.queue.append(
            SpeechItem(
                text=text,
                duration=duration,
                typingDelayMs=typing_delay
            )
        )

        if not self.active:
            self._showNext()
    
    def _showNext(self):
        if self.shuttingDown:
            return

        if not self.queue:
            self.active = False
            self._nextTimer.stop()
            self.bubble.fadeOut()
            return

        self.active = True
        item = self.queue.popleft()

        self.bubble.startTyping(item.text, item.typingDelayMs)

        # schedule next message after duration
        self._nextTimer.stop()
        self._nextTimer.start(item.duration)

    def shutdown(self):
        self.shuttingDown = True
        self._nextTimer.stop()
        self.queue.clear()
        self.bubble.shutdown()

class LegacySpeechBubbleController(QWidget):
    def __init__(self, sprite: QWidget, refreshRate: int = 5):
        super().__init__(None)
        self.refreshRate = refreshRate

        self.sprite = sprite
        self.queue = deque()

        self.active = False
        self.shuttingDown = False
        self.tailDirection = "right"

        # window setup
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.NoFocus)

        self.windowOpacityEffect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.windowOpacityEffect)
        self.windowOpacityEffect.setOpacity(0.0)

        # current speech variables
        self.fullText = ""
        self.currentCharacterIndex = 0

        self.typeTimer = QTimer(self)
        self.typeTimer.timeout.connect(self._typeNextCharacter)

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

        # tail space margins
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, TAIL_WIDTH)
        layout.addWidget(self.label)

        # movement animation
        self.movementAnimation = QPropertyAnimation(self, b"pos")
        self.movementAnimation.setEasingCurve(QEasingCurve.OutCubic)

        # fade animation
        self.fadeAnimation = QPropertyAnimation(self.windowOpacityEffect, b"opacity")
        self.fadeAnimation.setEasingCurve(QEasingCurve.OutCubic)
        self.fadeAnimation.setDuration(ANIMATION_OPACITY_DURATION)
        self.fadeAnimation.finished.connect(self._onFadeFinished)

        # follow sprite
        self.followTimer = QTimer(self)
        self.followTimer.timeout.connect(self._reposition)
        self.followTimer.start(1000 // self.refreshRate)

        self.hide()

    # internal methods
    def mousePressEvent(self, event):
        if not self.typeTimer.isActive():
            return

        self.typeTimer.stop()
        self.label.setText(self.fullText)
        self.adjustSize()

    def _onFadeFinished(self):
        if self.windowOpacityEffect.opacity() > 0.001:
            return
        
        self.hide()

    def _showNext(self):
        if self.shuttingDown:
            return

        if not self.queue:
            self.active = False
            self.typeTimer.stop()

            self.fadeAnimation.stop()
            self.fadeAnimation.setStartValue(self.windowOpacityEffect.opacity())
            self.fadeAnimation.setEndValue(0.0)
            self.fadeAnimation.start()
            return

        # fade in
        self.fadeAnimation.stop()
        self.windowOpacityEffect.setOpacity(0.0)
        self.fadeAnimation.setStartValue(0.0)
        self.fadeAnimation.setEndValue(1.0)
        self.fadeAnimation.start()

        self.active = True
        text, duration, typing_delay = self.queue.popleft()

        self.fullText = text
        self.currentCharacterIndex = 0 

        self.label.setText("")
        self.adjustSize()
        self._reposition(force_show=True)

        self.typeTimer.start(typing_delay)

        self.raise_()
        QTimer.singleShot(duration, self._showNext)

    def _reposition(self, force_show: bool = False):
        if not self.sprite:
            return

        if self.isHidden() and not force_show:
            return

        if force_show:
            self.show()

        screen = self.sprite.screen().availableGeometry()
        sprite = self.sprite.frameGeometry()

        width, height = self.width(), self.height()

        x = sprite.right() + BORDER_MARGIN
        y = sprite.top() - height // 2

        # flip if need be
        if x + width > screen.right():
            x = sprite.left() - width - BORDER_MARGIN

        # clamp vertically
        y = max(
            screen.top() + BORDER_MARGIN,
            min(y, screen.bottom() - height - BORDER_MARGIN)
        )

        # tail direction
        bubble_center_x = x + width // 2
        sprite_center_x = sprite.center().x()
    
        previous_tail_direciton = self.tailDirection
        self.tailDirection = "left" if sprite_center_x < bubble_center_x else "right"
        
        # force repaint if tail direction changed
        if previous_tail_direciton != self.tailDirection:
            self.update()

        self._animateTo(QPoint(x, y))

    def _animateTo(self, target: QPoint):
        if (self.pos() - target).manhattanLength() < 2:
            self.move(target)
            return

        if self.movementAnimation.state() == QPropertyAnimation.Running:
            self.movementAnimation.stop()

        distance = (self.pos() - target).manhattanLength()
        self.movementAnimation.setDuration(min(300, max(80, distance)))
        self.movementAnimation.setStartValue(self.pos())
        self.movementAnimation.setEndValue(target)
        self.movementAnimation.start()

    def _typeNextCharacter(self):
        if self.shuttingDown:
            self.typeTimer.stop()
            return

        if self.currentCharacterIndex >= len(self.fullText):
            self.typeTimer.stop()
            return
        
        self.currentCharacterIndex += 1
        self.label.setText(self.fullText[:self.currentCharacterIndex])
        self.adjustSize()

        previousCharacter = self.fullText[
            self.currentCharacterIndex-1:self.currentCharacterIndex
        ]

        if previousCharacter.isalnum():
            self.sprite.Sound.playSpeechBlip()

    # internal tail painting method
    def paintEvent(self, event):
        super().paintEvent(event)
        self._paintTail()

    def _paintTail(self):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(BACKGROUND_COLOR)
        painter.setPen(Qt.NoPen)

        label_rect = self.label.geometry()
        base_x = label_rect.center().x()
        base_y = label_rect.bottom()

        if self.tailDirection == "left":
            tip = QPoint(base_x - TAIL_WIDTH, base_y + TAIL_WIDTH)
        else:
            tip = QPoint(base_x + TAIL_WIDTH, base_y + TAIL_WIDTH)

        left = QPoint(base_x - TAIL_WIDTH // 2, base_y)
        right = QPoint(base_x + TAIL_WIDTH // 2, base_y)

        painter.drawPolygon(QPolygon([left, tip, right]))

    # external methods
    def addSpeech(self, text: str, duration: int | None = None):
        if self.shuttingDown:
            return

        typing_delay = (1000 // random.randint(*CHARACTERS_PER_SECOND))

        if duration is None:
            wordCount = len(text.split())
            characterCount = len(text)

            timeTyping = characterCount * typing_delay
            timeReading = (wordCount / READING_WPS) * 1000

            duration = max(timeTyping + timeReading + READING_DELAY, 3000)

        self.queue.append((text, duration, typing_delay))
        if not self.active:
            self._showNext()
    
    def shutdown(self):
        self.shuttingDown = True
        self.followTimer.stop()
        self.typeTimer.stop()
        self.fadeAnimation.stop()
        self.movementAnimation.stop()
        self.hide()
