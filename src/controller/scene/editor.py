from .model import SceneModel, DecorationEntity

from PySide6.QtCore import QObject, QPointF, Qt
from PySide6.QtGui import QCursor

from typing import Callable, Optional
from dataclasses import dataclass

from uuid import uuid4

@dataclass
class DragState:
    entityId: str
    globalOffset: QPointF
    
    # QWidget/QGraphicsWidget
    grabWidget: object

class SceneEditorController(QObject):
    def __init__(
        self,
        system,
        sprite = None
    ):
        super().__init__(sprite)

        # if any of these references are inaccessible
        # then something is very wrong
        self.model = system.model
        self.decorationSizeProvider = system.getDecorationSize
        self.viewportProvider = system.getViewportAtPoint
        
        self.placementName = None
        self.isDragging = False
        self.canEdit = False

    # internal methods
    def getGlobalPositionFromEvent(self, event) -> QPointF:
        try:
            return QPointF(event.globalPosition())
        except Exception:
            pass

        try:
            eventGlobalPosition = event.globalPos()

            return QPointF(
                eventGlobalPosition.x(), eventGlobalPosition.y()
            )
        except Exception:
            pass

        globalCursorPosition = QCursor.pos()

        return QPointF(
            globalCursorPosition.x(), globalCursorPosition.y()
        )
    
    def clampToViewport(
        self,
        globalPoint: QPointF,
        decorationName: str
    ) -> QPointF:
        viewport = self.viewportProvider(globalPoint)

        if viewport is None:
            return globalPoint

        viewpointBounds = viewport.globalRect()
        width, height = self.decorationSizeProvider(decorationName)

        clampedX = max(
            viewpointBounds.left(),
            min(viewpointBounds.right() - width, globalPoint.x())
        )
    
        clampedY = max(
            viewpointBounds.top(),
            min(viewpointBounds.bottom() - height, globalPoint.y())
        )

        return QPointF(clampedX, clampedY)

    # item hooks
    def beginDrag(
        self,
        entityId: str,
        grabWidget = None,
        mouseGlobal: QPointF = None
    ):
        if not self.canEdit:
            return
        
        entity = self.model.getEntity(entityId)

        if entity is None:
            return
        
        offset = mouseGlobal - entity.globalPosition

        self.dragObject = DragState(
            entityId=entityId,
            globalOffset=offset,
            grabWidget=grabWidget
        )

        try:
            grabWidget.grabMouse()
        except Exception:
            pass
    
    def attemptRemove(self, entityId: str):
        self.model.removeEntity(entityId)

    # viewport hooks
    def handleViewMousePress(self, viewport, event) -> bool:
        if not self.edit_enabled:
            return False

        if self.placementName is None:
            return False
        
        button = event.button()

        if button == Qt.RightButton:
            self.emptyPlacement()

            try:
                viewport.unsetPlacementCursor()
            except Exception:
                pass

            event.accept()
            return True
        
        if button != Qt.LeftButton:
            return False
        
        decorationName = self.placementName
        
        mouseGlobalPosition = self.getGlobalPositionFromEvent(event)
        width, height = self.decorationSizeProvider(decorationName)
        
        # center the placement at the cursor
        target = QPointF(
            mouseGlobalPosition.x() - width / 2.0,
            mouseGlobalPosition.y() - height / 2.0
        )

        clampedPosition = self.clampToViewport(target, decorationName)

        newEntity = DecorationEntity(
            entityId=str(uuid4()),
            name=decorationName,
            x=clampedPosition.x(),
            y=clampedPosition.y()
        )

        self.model.addEntity(newEntity)

        self.emptyPlacement()

        try:
            viewport.unsetPlacementCursor()
        except Exception:
            pass

        event.accept()
        return True
    
    def handleViewMouseMove(self, viewport, event) -> bool:
        if self.dragObject is None:
            return False
        
        mouseGlobalPosition = self.getGlobalPositionFromEvent(event)
        entity = self.model.getEntity(self.dragObject.entityId)

        if entity is None:
            return False
            
        clampedPosition = self.clampToViewport(
            mouseGlobalPosition - self.dragObject.globalOffset, # target
            entity.name
        )

        self.model.updateEntity(
            entityId=entity.entityId,
            position=clampedPosition
        )

        event.accept()
        return True

    # public methods
    def setEditing(self, editing: bool):
        self.canEdit = editing
    
    def beginPlacement(self, name: str):
        self.placementName = name
    
    def emptyPlacement(self):
        self.placementName = None
    