from ..interfaces.base.styling import CLOSE_STR

from .editor import SceneEditorController

from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtCore import QPointF, QRectF, Qt

from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsProxyWidget,
    QToolButton
)

BUTTON_RADIUS = 8

class RemoveDecorationButton(QGraphicsProxyWidget):
    def __init__(
        self,
        parent: QGraphicsItem,
        onClick = None
    ):
        super().__init__(parent)

        self.setZValue(999999) # should be good enough :>

        button = QToolButton()
        button.setCursor(Qt.PointingHandCursor)
        button.setText("✕")
        button.setFixedSize(BUTTON_RADIUS * 2, BUTTON_RADIUS * 2)

        # TODO: change styling later... too tired rn
        button.setStyleSheet(
            f"""
            QToolButton {{
                border: 1px solid rgba(160,40,40,255);
                border-radius: {BUTTON_RADIUS}px;
                background: rgba(220,70,70,220);
                color: rgba(255,255,255,255);
                font-weight: 700;
                padding: 0px;
            }}

            QToolButton:hover {{ background: rgba(235,90,90,235); }}
            QToolButton:pressed {{ background: rgba(190,55,55,235); }}
            """
        )

        button.clicked.connect(onClick)
        self.setWidget(button)

class DecorationGraphicsItem(QGraphicsPixmapItem):
    def __init__(
        self,
        entityId: str,
        name: str,
        pixmap: QPixmap,
        editor: SceneEditorController = None,
        grabWidget = None
    ):
        super().__init__(pixmap)

        self.entityId = entityId
        self.name = name

        self.editor = editor
        self.grabWidget = grabWidget

        self.setShapeMode(QGraphicsPixmapItem.BoundingRectShape)
        self.setAcceptedMouseButtons(Qt.LeftButton)

        self.removeButton = RemoveDecorationButton(
            self,
            onClick=self.onRemoveClicked
        )

        self.removeButton.setVisible(False)
        self._repositionRemoveButton()
    
    def setEditMode(self, visible: bool):
        self.removeButton.setVisible(visible)
    
    def setPixmap(self, pixmap: QPixmap):
        super().setPixmap(pixmap)
        self._repositionRemoveButton()

    def mousePressEvent(self, event):
        if (event.button() != Qt.LeftButton) or (not self.editor.canEdit):
            super().mousePressEvent(event)
            return
        
        mouseGlobalPosition = self.editor.getGlobalPositionFromEvent(event)

        self.editor.beginDrag(
            self.entityId,
            grabWidget=self.grabWidget,
            mouseGlobal=mouseGlobalPosition
        )

        event.accept()

    def _repositionRemoveButton(self):
        try:
            center = self.boundingRect().center()
            self._removeButton.setPos(
                center - QPointF(BUTTON_RADIUS, BUTTON_RADIUS)
            )

        except Exception:
            pass