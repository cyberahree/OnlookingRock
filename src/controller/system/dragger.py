from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import Qt

from typing import Callable, Optional

class WindowDragger:
    def __init__(
            self,
            widget,
            onDragStart: Optional[Callable] = None,
            onDragEnd: Optional[Callable] = None
        ):
        self.widget = widget
        self.onDragStart = onDragStart
        self.onDragEnd = onDragEnd
        
        self.isDragging = False
        self.dragDelta = None
    
    def handleMousePress(self, event) -> None:
        if event.button() != Qt.LeftButton:
            return
        
        self.dragDelta = event.globalPosition().toPoint() - self.widget.pos()
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
                screenBounds.right() - self.widget.width()
            )
        )
        
        finalY = max(
            screenBounds.top(),
            min(
                targetPos.y(),
                screenBounds.bottom() - self.widget.height()
            )
        )
        
        self.widget.move(finalX, finalY)
    
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
