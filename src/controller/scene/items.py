from .editor import SceneEditorController

from PySide6.QtWidgets import QGraphicsItem, QGraphicsPixmapItem
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtCore import QPointF, QRectF, Qt

BUTTON_RADIUS = 8

class RemoveDecorationButton(QGraphicsItem):
    def __init__(
        self,
        parent:
        QGraphicsItem,
        onClick,
        radius: int = BUTTON_RADIUS,
        padding: int = 4
    ):
        super().__init__(parent)
        self.radius = float(radius)
        self.padding = float(padding)
        self.onClick = onClick
        self.isHovering = False

        self.setZValue(999999)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)

    # override to give it a larger area
    def boundingRect(self) -> QRectF:
        radius = self.radius + self.padding
        return QRectF(-radius, -radius, 2 * radius, 2 * radius)

    def paint(self, painter: QPainter, option, widget=None):
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
        self.isHovering = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.isHovering = False
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            try:
                if self.onClick is not None:
                    self.onClick()
            finally:
                event.accept()

            return

        super().mousePressEvent(event)

class DecorationGraphicsItem(QGraphicsPixmapItem):
    def __init__(
        self,
        entityId: str,
        name: str,
        pixmap: QPixmap,
        editor: SceneEditorController | None = None,
        grabWidget=None,
    ):
        super().__init__(pixmap)

        self.entityId = entityId
        self.name = name
        self.editor = editor
        self.grabWidget = grabWidget

        self.setShapeMode(QGraphicsPixmapItem.BoundingRectShape)
        self.setAcceptedMouseButtons(Qt.LeftButton)

        self.removeHandle = RemoveDecorationButton(
            self,
            onClick=lambda: (
                self.editor.attemptRemove(self.entityId) if self.editor else None
            )
        )

        self.removeHandle.setVisible(False)
        self._repositionRemoveHandle()

    def setEditMode(self, visible: bool):
        self.removeHandle.setVisible(bool(visible))

    def setPixmap(self, pixmap: QPixmap):
        super().setPixmap(pixmap)
        self._repositionRemoveHandle()

    def mousePressEvent(self, event):
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
        try:
            center = self.boundingRect().center()
            self.removeHandle.setPos(center)
        except Exception:
            pass
