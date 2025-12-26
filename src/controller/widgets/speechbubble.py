from PySide6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtGui import QFont, QPainter, QPolygon, QColor

from collections import deque

SPEECH_BACKGROUND_COLOR = QColor(255, 255, 224, 255)
TAIL_WIDTH = 12

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
    def _showNext(self):
        if not self.queue:
            self.active = False
            self.hide()
            return

        self.active = True
        text, duration = self.queue.popleft()

        self.label.setText(text)
        self.adjustSize()
        self._reposition(force_show=True)

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
        if duration is None:
            duration = max(2000, len(text) * 45)

        self.queue.append((text, duration))
        if not self.active:
            self._showNext()