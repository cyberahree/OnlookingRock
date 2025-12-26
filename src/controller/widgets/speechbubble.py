from PySide6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtGui import QFont

from collections import deque

REFRESH_RATE = 15 # frames per second
SPEECH_MARGIN = 8

class SpeechBubble(QWidget):
    def __init__(self, sprite: QWidget):
        super().__init__()

        self.sprite = sprite

        self.speechQueue = deque()
        self.speechActive = False

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.NoFocus)

        # animations
        self.moveAnimation = QPropertyAnimation(self, b"pos")
        self.moveAnimation.setDuration(1000 // REFRESH_RATE)
        self.moveAnimation.setEasingCurve(QEasingCurve.OutCubic)

        # speech label
        self.label = QLabel("")
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label.setMaximumWidth(220)

        # font
        font = QFont("Comic Sans MS")
        font.setPointSize(11)
        
        self.label.setFont(font)

        # stylesheet
        self.label.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 224, 220);
                color: #222;
                padding: 8px 10px;
                border-radius: 10px;
            }
        """)

        # layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)

        self.hide()

        # repositioning
        self.repositionTimer = QTimer(self)
        self.repositionTimer.timeout.connect(self._reposition)
        self.repositionTimer.start(1000 // REFRESH_RATE)

    # internal methods
    def _calculateSpeechDurationMs(self, text: str) -> int:
        return max(2000, (len(text) / 200) * 60000)
    
    def _animateTo(self, target: QPoint) -> None:
        if self.moveAnimation.state() == QPropertyAnimation.Running:
            self.moveAnimation.stop()

        if (self.pos() - target).manhattanLength() < 3:
            self.move(target)
            return

        distance = (self.pos() - target).manhattanLength()

        self.moveAnimation.setDuration(min(300, max(80, distance)))
        self.moveAnimation.setStartValue(self.pos())
        self.moveAnimation.setEndValue(target)
        self.moveAnimation.start()

        self.raise_()

    def _reposition(self, revealSpeechBubble: bool = False) -> None:
        if self.sprite is None:
            return
        
        if self.isHidden() and not revealSpeechBubble:
            return
        elif revealSpeechBubble:
            self.show()
        
        screenBounds = self.sprite.screen().availableGeometry()
        spriteBounds = self.sprite.geometry()

        finalBubbleX = spriteBounds.right() + SPEECH_MARGIN
        finalBubbleY = spriteBounds.top() + (SPEECH_MARGIN / 2) - self.height()

        if finalBubbleX + self.width() > screenBounds.right():
            finalBubbleX = spriteBounds.left() - self.width() - SPEECH_MARGIN

        # clamp to screen vertically
        finalBubbleY = max(
            screenBounds.top() + SPEECH_MARGIN,
            min(
                finalBubbleY,
                screenBounds.bottom() - self.height() - SPEECH_MARGIN
            )
        )

        # flip if above screen
        if finalBubbleY < screenBounds.top() + SPEECH_MARGIN:
            finalBubbleY = spriteBounds.bottom() + SPEECH_MARGIN
        
        self._animateTo(QPoint(finalBubbleX, finalBubbleY))

    def _showNext(self) -> None:
        if not self.speechQueue:
            self.speechActive = False
            self.hide()
            return

        self.speechActive = True
        text, duration = self.speechQueue.popleft()

        self.label.setText(text)
        self.adjustSize()

        self._reposition(True)
        self.raise_()
        self.activateWindow()

        QTimer.singleShot(duration, self._showNext)

    # speech methods
    def addSpeech(self, text: str, duration: int = None) -> None:
        if duration is None:
            duration = self._calculateSpeechDurationMs(text)
        else:
            duration = max(duration, 500)  # minimum duration

        self.speechQueue.append((text, duration))

        if not self.speechActive:
            self._showNext()