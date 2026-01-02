from .model import DecorationEntity

from PySide6.QtCore import QObject, QPointF, Qt
from PySide6.QtGui import QCursor

from dataclasses import dataclass
from typing import Optional

from uuid import uuid4

@dataclass
class DragState:
    entityId: str
    globalOffset: QPointF
    grabWidget: object # QWidget/QGraphicsWidget

class SceneEditorController(QObject):
    def __init__(
        self,
        system,
        sprite = None
    ):
        super().__init__(sprite)

        self.system = system

        # if any of these references are inaccessible
        # then something is very wrong
        self.model = system.model
        self.decorationSizeProvider = system.getDecorationSize
        self.viewportProvider = system.getViewportAtPoint
        
        self.placementName: Optional[str] = None
        self.canEdit: bool = False

        self.dragObject: Optional[DragState] = None

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

        viewpointBounds = viewport.globalBounds()
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

    def clampToBounds(
        self,
        bounds,
        globalPoint: QPointF,
        decorationName: str
    ) -> QPointF:
        try:
            width, height = self.decorationSizeProvider(decorationName)
        except Exception:
            width, height = (32, 32)

        clampedX = max(
            bounds.left(),
            min(bounds.right() - width, globalPoint.x())
        )

        clampedY = max(
            bounds.top(),
            min(bounds.bottom() - height, globalPoint.y())
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
        
        if mouseGlobal is None:
            mouseGlobal = self.getGlobalPositionFromEvent(None)

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
        if self.placementName is None:
            return False
        
        button = event.button()

        if button == Qt.RightButton:
            try:
                self.system.endPlacement()
            except Exception:
                self.emptyPlacement()

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

        try:
            bounds = viewport.globalBounds()
            clampedPosition = self.clampToBounds(bounds, target, decorationName)
        except Exception:
            clampedPosition = self.clampToViewport(target, decorationName)

        newEntity = DecorationEntity(
            entityId=str(uuid4()),
            name=decorationName,
            x=clampedPosition.x(),
            y=clampedPosition.y()
        )

        self.model.addEntity(newEntity)

        try:
            self.system.endPlacement()
        except Exception:
            self.emptyPlacement()

        event.accept()
        return True
    
    def handleViewMouseMove(self, viewport, event) -> bool:
        # placement ghost (no click needed)
        if (self.dragObject is None) and (self.placementName is not None):
            try:
                decorationName = self.placementName
                mouseGlobalPosition = self.getGlobalPositionFromEvent(event)
                width, height = self.decorationSizeProvider(decorationName)

                target = QPointF(
                    mouseGlobalPosition.x() - width / 2.0,
                    mouseGlobalPosition.y() - height / 2.0
                )

                try:
                    bounds = viewport.globalBounds()
                    clampedPosition = self.clampToBounds(bounds, target, decorationName)
                except Exception:
                    clampedPosition = self.clampToViewport(target, decorationName)

                try:
                    viewport.showGhostAt(clampedPosition, decorationName)
                except Exception:
                    pass

                event.accept()
                return True
            except Exception:
                # don't interfere with normal interaction if anything fails xd
                return False

        # dragging existing entities
        if self.dragObject is None:
            return False

        mouseGlobalPosition = self.getGlobalPositionFromEvent(event)
        entity = self.model.getEntity(self.dragObject.entityId)

        if entity is None:
            return False

        # top-left position in global coords
        newGlobalPosition = mouseGlobalPosition - self.dragObject.globalOffset
        clampedPosition = self.clampToViewport(newGlobalPosition, entity.name)

        self.model.updateEntity(
            self.dragObject.entityId,
            position=clampedPosition
        )

        event.accept()
        return True

    def handleViewMouseRelease(self, viewport, event) -> bool:
        if self.dragObject is None:
            return False

        try:
            if self.dragObject.grabWidget is not None:
                self.dragObject.grabWidget.releaseMouse()
        except Exception:
            pass

        self.dragObject = None
        event.accept()

        return True

    # public methods
    def setEditing(self, editing: bool):
        self.canEdit = editing

        if not editing:
            # safety: ensure we don't keep grabbing input
            try:
                if self.dragObject and self.dragObject.grabWidget is not None:
                    self.dragObject.grabWidget.releaseMouse()
            except Exception:
                pass

            self.dragObject = None
            self.emptyPlacement()
    
    def beginPlacement(self, name: str):
        self.placementName = name
    
    def emptyPlacement(self):
        self.placementName = None
