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
    """
    manages scene editing including entity dragging and decoration placement
    """

    def __init__(
        self,
        system,
        sprite: Optional[QObject] = None
    ):
        """
        initialise the scene editor controller with system references.
        
        :param system: The scene system
        :param sprite: Optional sprite widget parent
        """

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
        """
        extract global mouse position from event with fallback strategies.
        
        :param event: The event object (may be None)
        :return: The global mouse position
        :rtype: QPointF
        """

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
        """
        clamp a position to the bounds of the viewport containing the point.
        
        :param globalPoint: The position to clamp in global coordinates
        :type globalPoint: QPointF
        :param decorationName: The decoration name to get size for
        :type decorationName: str
        :return: The clamped position
        :rtype: QPointF
        """

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
        """
        clamp a position to specific rectangular bounds.
        
        :param bounds: The bounding rectangle
        :param globalPoint: The position to clamp
        :type globalPoint: QPointF
        :param decorationName: The decoration name to get size for
        :type decorationName: str
        :return: The clamped position
        :rtype: QPointF
        """

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
        grabWidget: object | None = None,
        mouseGlobal: Optional[QPointF] = None
    ):
        """
        start dragging a decoration entity.
        
        :param entityId: The ID of the entity to drag
        :type entityId: str
        :param grabWidget: The widget that grabbed the mouse
        :param mouseGlobal: The global mouse position (auto-detected if None)
        :type mouseGlobal: QPointF
        """

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
    
    def attemptRemove(self, entityId: str):
        """
        attempt to remove a decoration entity from the scene.
        
        :param entityId: The ID of the entity to remove
        :type entityId: str
        """

        self.model.removeEntity(entityId)

    # viewport hooks
    def handleViewMousePress(self, viewport, event) -> bool:
        """
        handle mouse press in viewport for placement or dragging.
        
        :param viewport: The viewport window
        :param event: The mouse press event
        :return: True if event was handled, False otherwise
        :rtype: bool
        """

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
        """
        handle mouse movement for ghost preview or entity dragging.
        
        :param viewport: The viewport window
        :param event: The mouse move event
        :return: True if event was handled, False otherwise
        :rtype: bool
        """

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
        """
        handle mouse release to end entity dragging.
        
        :param viewport: The viewport window
        :param event: The mouse release event
        :return: True if event was handled, False otherwise
        :rtype: bool
        """

        if self.dragObject is None:
            return False

        self.dragObject = None
        event.accept()

        return True

    # public methods
    def setEditing(self, editing: bool):
        """
        enable or disable edit mode.
        
        :param editing: True to enable editing, False to disable
        :type editing: bool
        """

        self.canEdit = editing

        if not editing:
            # safety: ensure we don't keep dragging if edit mode was disabled
            self.dragObject = None
            self.emptyPlacement()
    
    def beginPlacement(self, name: str):
        """
        start placement mode for a decoration type.
        
        :param name: The name of the decoration to place
        :type name: str
        """

        self.placementName = name
    
    def emptyPlacement(self):
        """
        clear the current placement type.
        """

        self.placementName = None
