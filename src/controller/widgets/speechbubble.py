from PySide6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtGui import QFont, QPainter, QPolygon, QColor

from collections import deque

import random

SPEECH_BACKGROUND_COLOR = QColor(255, 255, 224, 255)
TAIL_WIDTH = 12

CHARACTERS_PER_SECOND = (25, 45)
READING_DELAY = 4500
READING_WPS = (180 / 60) # words per second
REFRESH_RATE = 15 # frames per second
SPEECH_MARGIN = 8

class SpeechBubble(QWidget):
    def __init__(self, sprite: QWidget):
        super().__init__(None)

        self.sprite = sprite
        self.queue = deque()

        self.active = False
        self.tailDirection = "right"

        # window setup
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.NoFocus)

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

        font = QFont("Comic Sans MS", 11)
        self.label.setFont(font)

        rgba = SPEECH_BACKGROUND_COLOR.getRgb()
        self.label.setStyleSheet(f"""
            QLabel {{
                background-color: rgba({rgba[0]}, {rgba[1]}, {rgba[2]}, {rgba[3]});
                color: #222;
                padding: 8px 10px;
                border-radius: 10px;
            }}
        """)

        # tail space margins
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, TAIL_WIDTH)
        layout.addWidget(self.label)

        # movement animation
        self.movementAnimation = QPropertyAnimation(self, b"pos")
        self.movementAnimation.setEasingCurve(QEasingCurve.OutCubic)

        # follow sprite
        self.followTimer = QTimer(self)
        self.followTimer.timeout.connect(self._reposition)
        self.followTimer.start(1000 // REFRESH_RATE)

        self.hide()

    # internal methods
    def mousePressEvent(self, event):
        if not self.typeTimer.isActive():
            return

        self.typeTimer.stop()
        self.label.setText(self.fullText)
        self.adjustSize()

    def _showNext(self):
        if not self.queue:
            self.active = False
            self.typeTimer.stop()
            self.hide()
            return

        self.active = True
        text, duration, typing_delay = self.queue.popleft()

        self.fullText = text
        self.curentCharacterIndex = 0

        self.label.setText(text)
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
        sprite = self.sprite.geometry()

        x = sprite.right() + SPEECH_MARGIN
        y = sprite.top() - self.height() // 2

        # flip if need be
        if x + self.width() > screen.right():
            x = sprite.left() - self.width() - SPEECH_MARGIN

        # clamp vertically
        y = max(
            screen.top() + SPEECH_MARGIN,
            min(y, screen.bottom() - self.height() - SPEECH_MARGIN)
        )

        # tail direction
        bubble_center_x = x + self.width() // 2
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
        if self.currentCharacterIndex >= len(self.fullText):
            self.typeTimer.stop()
            return
        
        self.currentCharacterIndex += 1
        self.label.setText(self.fullText[:self.currentCharacterIndex])
        self.adjustSize()

    # internal tail painting method
    def paintEvent(self, event):
        super().paintEvent(event)
        self._paintTail()

    def _paintTail(self):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(SPEECH_BACKGROUND_COLOR)
        painter.setPen(Qt.NoPen)

        label_rect = self.label.geometry()
        base_x = label_rect.center().x()
        base_y = label_rect.bottom()

        if self.tailDirection == "left":
            tip = QPoint(base_x - TAIL_WIDTH, base_y + TAIL_WIDTH)
        else:
            tip = QPoint(base_x + TAIL_WIDTH, base_y + TAIL_WIDTH)

        left = QPoint(base_x - TAIL_WIDTH / 2, base_y)
        right = QPoint(base_x + TAIL_WIDTH / 2, base_y)

        painter.drawPolygon(QPolygon([left, tip, right]))

    # external methods
    def addSpeech(self, text: str, duration: int | None = None):
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