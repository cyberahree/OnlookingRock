from ..base.anchor import SpriteAnchorMixin
from ..base import InterfaceComponent

from ..base.styling import (
    BACKGROUND_COLOR,
    BORDER_MARGIN,
    BORDER_RADIUS,
    DEFAULT_FONT,
    PADDING,
    TEXT_COLOR,
    asRGB,
)

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget, QLineEdit, QHBoxLayout
from PySide6.QtCore import Qt, QTimer, QPoint, Signal, QSize
from PySide6.QtGui import QPainter, QPolygon

from typing import Callable, Iterable, Optional

import random

CHARACTERS_PER_SECOND = (25, 45)
MAX_WIDTH = 220
TAIL_SIZE = 12

class SpeechBubbleComponent(InterfaceComponent, SpriteAnchorMixin):
    typingFinished = Signal()
    fadeOutFinished = Signal()

    def __init__(
        self,
        sprite: QWidget,
        clock,
        blipSound: Optional[Callable[[], None]] = None,
        occludersProvider: Optional[Callable[[], Iterable[QWidget]]] = (lambda: []),
        keepOccludersOnTop: bool = True,
    ):
        super().__init__(sprite, clock)

        self.sprite = sprite
        self.blip = blipSound or (lambda: None)

        self.occludersProvider = occludersProvider
        self.keepOccludersOnTop = keepOccludersOnTop

        self.isShuttingDown = False
        self.tailDirection = "right"

        self.fullText = ""
        self.currentCharacterIndex = 0
        self.currentTypingDelay = CHARACTERS_PER_SECOND[0]

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

        # main bubble body (includes label + optional input)
        self.body = QWidget(self)
        self.body.setObjectName("speechBody")
        self.body.setStyleSheet(
            f"""
            QWidget#speechBody {{
                background-color: {asRGB(BACKGROUND_COLOR)};
                border-radius: {BORDER_RADIUS}px;
            }}
            """
        )

        bodyLayout = QVBoxLayout(self.body)
        bodyLayout.setContentsMargins(PADDING, PADDING, PADDING, PADDING)
        bodyLayout.setSpacing(max(4, PADDING // 2))

        self.label = QLabel("")
        self.label.setWordWrap(True)
        self.label.setMaximumWidth(MAX_WIDTH)
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label.setFont(DEFAULT_FONT)
        self.label.setStyleSheet(
            f"""
            QLabel {{
                background: transparent;
                color: {asRGB(TEXT_COLOR)};
            }}
            """
        )

        # prevent size hint issues
        self.label.setSizePolicy(
            self.label.sizePolicy().horizontalPolicy(),
            self.label.sizePolicy().verticalPolicy()
        )

        bodyLayout.addWidget(self.label)

        # input row (hidden by default)
        self.inputContainer = QWidget(self.body)
        inputLayout = QHBoxLayout(self.inputContainer)
        inputLayout.setContentsMargins(0, 0, 0, 0)
        inputLayout.setSpacing(0)

        inputLayout.addStretch(1)

        self.inputField = QLineEdit(self.inputContainer)
        self.inputField.setMaximumWidth(MAX_WIDTH)
        self.inputField.setAlignment(Qt.AlignRight)
        self.inputField.setFont(DEFAULT_FONT)
        self.inputField.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: {asRGB(BACKGROUND_COLOR)};
                color: {asRGB(TEXT_COLOR)};
                border: none;
            }}
            """
        )

        inputLayout.addWidget(self.inputField, 0, Qt.AlignRight)

        self.inputContainer.hide()
        bodyLayout.addWidget(self.inputContainer)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, TAIL_SIZE)
        layout.addWidget(self.body)

        self.typeTimer = QTimer(self)
        self.typeTimer.timeout.connect(self._typeNextCharacter)

        self.followTimer.start()

        # hacky fix:
        # prevent qt geometry warnings
        # i hate you qt
        self.setMinimumSize(40, 40)
        self.setMaximumSize(MAX_WIDTH + PADDING * 2 + 20, 16777215)  # Qt's default max height

        self.hide()

    def setInputVisible(self, visible: bool) -> None:
        if visible:
            self.inputContainer.show()

            # allow focusing/typing into the input
            self.setAttribute(Qt.WA_ShowWithoutActivating, False)
            self.setFocusPolicy(Qt.StrongFocus)
            self.inputField.setFocus(Qt.OtherFocusReason)
            try:
                self.activateWindow()
            except Exception:
                pass
        else:
            self.inputContainer.hide()

            # restore non-interactive behavior
            self.setAttribute(Qt.WA_ShowWithoutActivating, True)
            self.setFocusPolicy(Qt.NoFocus)
            self.inputField.clearFocus()

        self._updateSize()
        self._reposition(forceShow=self.isVisible())

    def configureInput(self, placeholder: str = "", text: str = "") -> None:
        self.inputField.setPlaceholderText(placeholder or "")
        self.inputField.setText(text or "")
        self.inputField.setCursorPosition(len(self.inputField.text()))

    def mousePressEvent(self, event) -> None:
        if self.typeTimer.isActive():
            self.skipTyping()

    def startTyping(
        self,
        text: str,
        typingDelay: Optional[int] = None,
        showInput: bool = False,
        inputPlaceholder: str = "",
        inputText: str = "",
    ) -> None:
        if self.isShuttingDown:
            return

        # reset interactive mode unless requested
        if showInput:
            self.configureInput(inputPlaceholder, inputText)
            self.setInputVisible(True)
        else:
            self.setInputVisible(False)

        if typingDelay is None:
            typingDelay = random.randint(
                CHARACTERS_PER_SECOND[0],
                CHARACTERS_PER_SECOND[1],
            )

        self.fullText = text
        self.currentCharacterIndex = 0
        self.currentTypingDelay = int(typingDelay)

        self.label.setText("")
        self._updateSize()
        self._reposition(forceShow=True)

        if showInput:
            # (re)focus after showing, otherwise focus calls before .show() can be ignored.
            try:
                self.inputField.setFocus(Qt.OtherFocusReason)
                self.activateWindow()
            except Exception:
                pass

        self.fadeIn()
        self.raise_()
        self.followTimer.start()

        if self.sprite:
            self.sprite.raise_()

        self.restackOccluders(self.occludersProvider)
        self.typeTimer.start(self.currentTypingDelay)

    def skipTyping(self) -> None:
        if not self.typeTimer.isActive():
            return

        self.stopTyping(showFullText=True)

    def stopTyping(self, showFullText: bool = False) -> None:
        if not self.typeTimer.isActive():
            return

        self.typeTimer.stop()

        if showFullText:
            self.label.setText(self.fullText)
            self._updateSize()

    def shutdown(self) -> None:
        self.isShuttingDown = True
        self.followTimer.stop()
        self.typeTimer.stop()
        self.fadeAnimation.stop()
        self.moveAnimation.stop()

        try:
            self.inputField.clearFocus()
        except Exception:
            pass

        self.hide()

    def _typeNextCharacter(self) -> None:
        if self.isShuttingDown:
            self.typeTimer.stop()
            return

        if self.currentCharacterIndex >= len(self.fullText):
            self.typeTimer.stop()
            self.typingFinished.emit()
            return

        self.currentCharacterIndex += 1
        self.label.setText(self.fullText[:self.currentCharacterIndex])
        self._updateSize()
        self._reposition()

        character = self.fullText[self.currentCharacterIndex - 1:self.currentCharacterIndex]

        if character.isalnum():
            try:
                self.blip()
            except Exception:
                pass

    def _handleFadeFinished(self, endOpacity: float) -> None:
        if endOpacity <= 0.001:
            self.fadeOutFinished.emit()

    def _updateSize(self) -> None:
        # let the label calculate its size based on content
        # and update the body to fit content
        self.label.adjustSize()
        self.body.adjustSize()
        
        # calculate desired size
        desired_size = self.body.sizeHint()
        
        # tail margin
        final_height = desired_size.height() + TAIL_SIZE
        final_width = desired_size.width()
        
        # enforce constraints
        min_size = self.minimumSize()
        max_size = self.maximumSize()
        
        final_width = max(min_size.width(), min(final_width, max_size.width()))
        final_height = max(min_size.height(), min(final_height, max_size.height()))
        
        # use .setFixedSize() temporarily to avoid Qt geometry conflicts
        self.setFixedSize(final_width, final_height)
        
        # then restore the constraints
        QTimer.singleShot(0, lambda: self._restoreSizeConstraints())
    
    def _restoreSizeConstraints(self) -> None:
        self.setMinimumSize(40, 40)
        self.setMaximumSize(MAX_WIDTH + PADDING * 2 + 20, 16777215)

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
            occludersProvider=self.occludersProvider,
        )

        prev_tail = self.tailDirection
        self.tailDirection = self.inwardHorizontalDirection(target)

        if prev_tail != self.tailDirection:
            self.update()

        self.animateTo(target)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)

        if not painter.isActive():
            return

        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(BACKGROUND_COLOR)
        painter.setPen(Qt.NoPen)

        label_rect = self.body.geometry()
        base_x = label_rect.center().x()
        base_y = label_rect.bottom()

        if self.tailDirection == "left":
            tip = QPoint(base_x - TAIL_SIZE, base_y + TAIL_SIZE)
        else:
            tip = QPoint(base_x + TAIL_SIZE, base_y + TAIL_SIZE)

        left = QPoint(base_x - TAIL_SIZE // 2, base_y)
        right = QPoint(base_x + TAIL_SIZE // 2, base_y)
        painter.drawPolygon(QPolygon([left, tip, right]))
