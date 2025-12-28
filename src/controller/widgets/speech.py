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
READING_WORDS_PER_SECOND = (180 / 60) # words per second

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
            sprite.soundManager.playSpeechBlip,
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
        
        typingDelay = (1000 // random.randint(*CHARACTERS_PER_SECOND))

        if duration is None:
            wordCount = len(text.split())
            characterCount = len(text)

            timeTyping = characterCount * typingDelay
            timeReading = (wordCount / READING_WORDS_PER_SECOND) * 1000

            duration = max(timeTyping + timeReading + READING_DELAY, 3000)
    
        self.queue.append(
            SpeechItem(
                text=text,
                duration=duration,
                typingDelayMs=typingDelay
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
