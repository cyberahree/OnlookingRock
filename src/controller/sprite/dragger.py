from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import Qt

from typing import Callable, Optional

class SpriteDragger:
    """
    handles sprite dragging with screen boundary clamping on release
    """

    def __init__(
        self,
        sprite,
        onDragStart: Optional[Callable[[], None]] = None,
        onDragEnd: Optional[Callable[[], None]] = None,
        canDrag: Optional[Callable[[], bool]] = None
    ):
        """
        initialise the sprite dragger with optional callbacks.
        
        :param sprite: The sprite widget to make draggable
        :param onDragStart: Callback invoked when drag begins
        :type onDragStart: Optional[Callable]
        :param onDragEnd: Callback invoked when drag ends
        :type onDragEnd: Optional[Callable]
        """

        self.sprite = sprite
        self.onDragStart = onDragStart
        self.onDragEnd = onDragEnd
        self.canDrag = canDrag or (lambda: True)

        self.isDragging = False
        self.dragDelta = None

    def handleMousePress(self, event) -> None:
        """
        handle mouse press to start dragging.
        
        :param event: The mouse press event
        """

        if event.button() != Qt.LeftButton:
            return

        if not self.canDrag():
            return

        self.dragDelta = event.globalPosition().toPoint() - self.sprite.pos()
        self.isDragging = True

        if self.onDragStart:
            self.onDragStart()

    def handleMouseMove(self, event) -> None:
        """
        handle mouse movement to update sprite position during drag.
        
        :param event: The mouse move event
        """

        if (event.buttons() != Qt.LeftButton) or (self.dragDelta is None):
            return

        globalPos = event.globalPosition().toPoint()
        targetPos = globalPos - self.dragDelta

        # move freely without clamping during drag
        self.sprite.move(targetPos.x(), targetPos.y())

    def handleMouseRelease(self, _event) -> None:
        """
        handle mouse release to end dragging and clamp sprite to screen bounds.
        
        :param _event: The mouse release event
        """

        if not self.isDragging:
            return

        # determine which screen the sprite is on
        screen = QGuiApplication.screenAt(self.sprite.geometry().center())
        
        if screen is None:
            screen = QGuiApplication.primaryScreen()

        # clamp to screen bounds after drag completes
        screenBounds = screen.availableGeometry()

        finalX = max(
            screenBounds.left(),
            min(
                self.sprite.x(),
                screenBounds.right() - self.sprite.width()
            )
        )

        finalY = max(
            screenBounds.top(),
            min(
                self.sprite.y(),
                screenBounds.bottom() - self.sprite.height()
            )
        )

        self.sprite.move(finalX, finalY)

        self.isDragging = False
        self.dragDelta = None

        if self.onDragEnd:
            self.onDragEnd()

    def reset(self):
        """
        reset the dragging state.
        """

        self.isDragging = False
        self.dragDelta = None
