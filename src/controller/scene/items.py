from .editor import SceneEditorController

from PySide6.QtWidgets import QGraphicsItem, QGraphicsPixmapItem, QGraphicsRectItem
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtCore import QPointF, QRectF, Qt

from typing import Callable, Optional

PLACEMENT_INDICATOR_RADIUS = 12
Z_REMOVE_BUTTON = 999999
BUTTON_RADIUS = 8

class RemoveDecorationButton(QGraphicsItem):
    """
    clickable delete button for removing decorations from the scene.
    """

    def __init__(
        self,
        parent:
        QGraphicsItem,
        onClick: Optional[Callable[[], None]],
        radius: int = BUTTON_RADIUS,
        padding: int = 4
    ):
        """
        initialise the remove button graphics item.
        
        :param parent: the parent graphics item
        :type parent: QGraphicsItem
        :param onClick: callback invoked when button is clicked
        :param radius: radius of the button circle
        :type radius: int
        :param padding: padding around the button
        :type padding: int
        """

        super().__init__(parent)
        self.radius = float(radius)
        self.padding = float(padding)
        self.onClick = onClick
        self.isHovering = False

        self.setZValue(Z_REMOVE_BUTTON)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)

    # override to give it a larger area
    def boundingRect(self) -> QRectF:
        """
        get the bounding rectangle of the button including padding.
        
        :return: the bounding rectangle
        :rtype: QRectF
        """

        radius = self.radius + self.padding
        return QRectF(-radius, -radius, 2 * radius, 2 * radius)

    def paint(self, painter: QPainter, _option, _widget=None):
        """
        paint the remove button with an X mark.
        
        :param painter: the painter to use for drawing
        :type painter: QPainter
        """

        painter.setRenderHint(QPainter.Antialiasing, True)

        # Background
        background = QColor(235, 90, 90, 235) if self.isHovering else QColor(220, 70, 70, 220)
        border = QColor(160, 40, 40, 255)

        painter.setPen(QPen(border, 1.0))
        painter.setBrush(background)
        painter.drawEllipse(
            QRectF(
                -self.radius,
                -self.radius,
                2 * self.radius,
                2 * self.radius
            )
        )

        # x mark
        pen = QPen(QColor(255, 255, 255, 255), 2.0)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)

        lineDistance = self.radius * 0.45
        painter.drawLine(QPointF(-lineDistance, -lineDistance), QPointF(lineDistance, lineDistance))
        painter.drawLine(QPointF(-lineDistance, lineDistance), QPointF(lineDistance, -lineDistance))

    def hoverEnterEvent(self, event):
        """
        handle hover enter event to highlight the button.
        
        :param event: the hover event
        """

        self.isHovering = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """
        handle hover leave event to unhighlight the button.
        
        :param event: the hover event
        """

        self.isHovering = False
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        """
        handle mouse press by invoking the onClick callback.
        
        :param event: the mouse press event
        """

        if event.button() == Qt.LeftButton:
            try:
                if self.onClick is not None:
                    self.onClick()
            finally:
                event.accept()

            return

        super().mousePressEvent(event)

class PlacementIndicator(QGraphicsItem):
    """
    visual indicator for decoration placement preview.
    """

    def __init__(
        self,
        radius: int = PLACEMENT_INDICATOR_RADIUS,
        padding: int = 4
    ):
        """
        initialise the placement indicator graphics item.
        
        :param radius: radius of the indicator circle
        :type radius: int
        :param padding: padding around the indicator
        :type padding: int
        """

        super().__init__()
        self.radius = float(radius)
        self.padding = float(padding)
        self.isHovering = False
        self.previewPixmap: QPixmap | None = None

        self.setZValue(999999)
        self.setAcceptedMouseButtons(Qt.NoButton)
        self.setAcceptHoverEvents(True)

    def setPreviewPixmap(self, pixmap: QPixmap | None):
        """
        set the preview pixmap for the placement indicator.
        
        :param pixmap: the pixmap to preview or None to clear
        :type pixmap: Optional[QPixmap]
        """

        self.previewPixmap = pixmap
        self.update()

    def boundingRect(self) -> QRectF:
        """
        get the bounding rectangle including padding.
        
        :return: the bounding rectangle
        :rtype: QRectF
        """

        radius = self.radius + self.padding
        return QRectF(-radius, -radius, 2 * radius, 2 * radius)

    def paint(self, painter: QPainter, option, widget=None):
        """
        paint the placement indicator with a crosshair.
        
        :param painter: the painter to use for drawing
        :type painter: QPainter
        :param option: the style option
        :param widget: the widget being painted on
        """

        painter.setRenderHint(QPainter.Antialiasing, True)

        background = QColor(90, 200, 90, 235) if self.isHovering else QColor(70, 180, 70, 220)
        border = QColor(40, 120, 40, 255)

        painter.setPen(QPen(border, 1.0))
        painter.setBrush(background)
        painter.drawEllipse(
            QRectF(
                -self.radius,
                -self.radius,
                2 * self.radius,
                2 * self.radius
            )
        )

        pen = QPen(QColor(255, 255, 255, 255), 2.0)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)

        lineDistance = self.radius * 0.4

        painter.drawLine(QPointF(-lineDistance, 0), QPointF(lineDistance, 0))
        painter.drawLine(QPointF(0, -lineDistance), QPointF(0, lineDistance))

    def hoverEnterEvent(self, event):
        """
        handle hover enter event to highlight the indicator.
        
        :param event: the hover event
        """

        self.isHovering = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """
        handle hover leave event to unhighlight the indicator.
        
        :param event: the hover event
        """

        self.isHovering = False
        self.update()
        super().hoverLeaveEvent(event)

class DecorationGraphicsItem(QGraphicsPixmapItem):
    """
    graphics item representing a decoration with edit controls.
    """

    def __init__(
        self,
        entityId: str,
        name: str,
        pixmap: QPixmap,
        editor: SceneEditorController | None = None,
        grabWidget: object | None = None,
    ):
        """
        initialise the decoration graphics item.
        
        :param entityId: unique identifier for the decoration entity
        :type entityId: str
        :param name: the name of the decoration
        :type name: str
        :param pixmap: the pixmap to display as the decoration
        :type pixmap: QPixmap
        :param editor: optional scene editor controller for delete functionality
        :type editor: Optional[SceneEditorController]
        :param grabWidget: optional widget to use for mouse tracking
        """

        super().__init__(pixmap)

        self.entityId = entityId
        self.name = name
        self.editor = editor
        self.grabWidget = grabWidget

        self.setShapeMode(QGraphicsPixmapItem.BoundingRectShape)
        self.setAcceptedMouseButtons(Qt.LeftButton)

        # hack alert: CERTAIN platforms do per-pixel hit testing for translucent
        # top level windows. this is not good for decorations that have a central
        # transparent pixel where the cursor is.

        # to avoid this, we add a nearly-invisible backdrop rectangle that covers
        # the full size of the pixmap
        self._hitProxy = QGraphicsRectItem(self)
        self._hitProxy.setZValue(-999999)
        self._hitProxy.setPen(QPen(Qt.NoPen))
        self._hitProxy.setBrush(QColor(0, 0, 0, 1))
        self._hitProxy.setRect(self.boundingRect())
        self._hitProxy.setAcceptedMouseButtons(Qt.NoButton)
        self._hitProxy.setVisible(False)

        self.removeHandle = RemoveDecorationButton(
            self,
            onClick=lambda: (
                self.editor.attemptRemove(self.entityId) if self.editor else None
            )
        )

        self.removeHandle.setVisible(False)
        self._repositionRemoveHandle()

    def setEditMode(self, visible: bool):
        """
        set the edit mode visibility of controls.
        
        :param visible: whether to show the edit controls
        :type visible: bool
        """

        self.removeHandle.setVisible(bool(visible))
        try:
            self._hitProxy.setVisible(bool(visible))
        except Exception:
            pass

    def setPixmap(self, pixmap: QPixmap):
        """
        set the pixmap for the decoration and update remove handle position.
        
        :param pixmap: the new pixmap to display
        :type pixmap: QPixmap
        """

        super().setPixmap(pixmap)
        self._repositionRemoveHandle()

        try:
            self._hitProxy.setRect(self.boundingRect())
        except Exception:
            pass

    def mousePressEvent(self, event):
        """
        handle mouse press to start dragging the decoration.
        
        :param event: the mouse press event
        """

        # clicking the remove handle is handled by the child item.
        if (event.button() != Qt.LeftButton) or (not getattr(self.editor, "canEdit", False)):
            super().mousePressEvent(event)
            return

        mouseGlobalPosition = self.editor.getGlobalPositionFromEvent(event) if self.editor else QPointF(0, 0)

        if self.editor:
            self.editor.beginDrag(
                self.entityId,
                grabWidget=self.grabWidget,
                mouseGlobal=mouseGlobalPosition,
            )

        event.accept()

    def _repositionRemoveHandle(self):
        """
        reposition the remove button to the centre of the decoration.
        """

        try:
            center = self.boundingRect().center()
            self.removeHandle.setPos(center)
        except Exception:
            pass

