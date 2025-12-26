from PySide6.QtCore import Qt, QElapsedTimer, QPointF
from PySide6.QtGui import QGuiApplication

from typing import Callable, Optional

class WindowDragger:
    def __init__(
        self,
        sprite,
        onDragStart: Optional[Callable] = None,
        onDragEnd: Optional[Callable] = None
    ):
        self.sprite = sprite
        self.onDragStart = onDragStart
        self.onDragEnd = onDragEnd

        self.isDragging = False
        self.dragDelta = None

    def handleMousePress(self, event) -> None:
        if event.button() != Qt.LeftButton:
            return

        self.dragDelta = event.globalPosition().toPoint() - self.sprite.pos()
        self.isDragging = True

        if self.onDragStart:
            self.onDragStart()

    def handleMouseMove(self, event) -> None:
        if (event.buttons() != Qt.LeftButton) or (self.dragDelta is None):
            return

        globalPos = event.globalPosition().toPoint()
        targetPos = globalPos - self.dragDelta

        # get target screen
        screen = QGuiApplication.screenAt(globalPos)

        if screen is None:
            screen = QGuiApplication.primaryScreen()

        # calculate application position restricted to screen bounds
        screenBounds = screen.availableGeometry()

        finalX = max(
            screenBounds.left(),
            min(
                targetPos.x(),
                screenBounds.right() - self.sprite.width()
            )
        )

        finalY = max(
            screenBounds.top(),
            min(
                targetPos.y(),
                screenBounds.bottom() - self.sprite.height()
            )
        )

        self.sprite.move(finalX, finalY)

    def handleMouseRelease(self, _event) -> None:
        if not self.isDragging:
            return

        self.isDragging = False
        self.dragDelta = None

        if self.onDragEnd:
            self.onDragEnd()

    def reset(self):
        self.isDragging = False
        self.dragDelta = None
