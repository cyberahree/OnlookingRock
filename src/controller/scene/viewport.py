from .model import DecorationEntity, SceneModel
from .editor import SceneEditorController
from .items import DecorationGraphicsItem

from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QWidget
from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QPainter, QPixmap, QScreen

from typing import Dict, Callable

class DecorationScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemIndexMethod(QGraphicsScene.NoIndex)

class DecorationView(QGraphicsView):
    def __init__(
        self,
        viewportWindow: "SceneViewportWindow",
        scene: QGraphicsScene,
        editor: SceneEditorController
    ):
        super().__init__(viewportWindow)
        self.setScene(scene)

        self.viewportWindow = viewportWindow
        self.editor = editor

        self.setFrameShape(QGraphicsView.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)

        # :sob:
        self.setStyleSheet("background: transparent;")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setFocusPolicy(Qt.NoFocus)

    # a bunch of safe-exiting event handlers that just pass to the editor
    # if not handled, pass through to super()
    def mousePressEvent(self, event):
        try:
            if self.editor.handleViewMousePress(self.viewportWindow, event):
                return
        except Exception:
            pass

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        try:
            if self.editor.handleViewMouseMove(self.viewportWindow, event):
                return

        except Exception:
            pass

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        try:
            if self.editor.handleViewMouseRelease(self.viewportWindow, event):
                return
        except Exception:
            pass
        super().mouseReleaseEvent(event)

class SceneViewportWindow(QWidget):
    def __init__(
        self,
        screen: QScreen,
        clock = None,
        model: SceneModel = None,
        editor: SceneEditorController = None,
        system = None,
    ):
        super().__init__(None)

        self.screen = screen
        self.model = model
        self.editor = editor

        self.decorationPixmapProvider = system.getDecorationPixmap

        self.inEditMode = False

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.NoFocus)

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus
        )

        screenGeometry = self.screen.geometry()
        self.setGeometry(screenGeometry)

        self.scene = DecorationScene(self)
        self.view = DecorationView(
            self,
            self.scene,
            editor
        )

        self.view.setGeometry(
            self.rect()
        )

        self.items: Dict[str, DecorationGraphicsItem] = {}

        self.updateSceneBounds()
        self.show()

        self.model.entityAdded.connect(self._onEntityChanged)
        self.model.entityUpdated.connect(self._onEntityChanged)
        self.model.entityRemoved.connect(self._onEntityRemoved)

        # TODO: implement physics
        clock.timer.timeout.connect(lambda: None)

    # events
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.view.setGeometry(self.rect())
        self._updateSceneRect()

    # internal methods
    def _updateSceneRect(self):
        self.scene.setSceneRect(
            QRectF(
                0, 0,
                self.width(),
                self.height()
            )
        )
    
    def _viewportOriginalGlobal(self) -> QPointF:
        geometry = self.screen.geometry()

        return QPointF(
            geometry().left(),
            geometry().top()
        )

    def _shouldContain(
        self,
        entity: DecorationEntity,
        pixmap: QPixmap
    ) -> bool:
        width = pixmap.width()
        height = pixmap.height()
        
        centre = QPointF(entity.x + width / 2.0, entity.y + height / 2.0)
        return self.globalBounds().contains(centre)
    
    def _onEntityChanged(
        self,
        entity: DecorationEntity
    ):
        name = entity.name
        pixmap = self.decorationPixmapProvider(entity.name)

        if (pixmap is None) or (pixmap.isNull()):
            return
        
        shouldContain = self._shouldContain(entity, pixmap)
        existing = self.items.get(entity.entityId, None)

        if not shouldContain:
            # remove if exists
            if existing is not None:
                try:
                    self.scene.removeItem(existing)
                except Exception:
                    pass

                self.items.pop(entity.entityId, None)

            return
        
        if existing is None:
            # create new item
            decorationItem = DecorationGraphicsItem(
                entityId=entity.entityId,
                name=name,
                pixmap=pixmap,
                editor=self.editor,
                grabWidget=self.view
            )

            decorationItem.setEditMode(self.inEditMode)
            existing = decorationItem
            
            self.scene.addItem(decorationItem)
            self.items[entity.entityId] = decorationItem
        else:
            # update existing item
            if existing.name != name:
                existing.name = name
                existing.setPixmap(pixmap)

        origin = self._viewportOriginalGlobal()

        relativePosition = QPointF(
            entity.x - origin.x(),
            entity.y - origin.y()
        )

        existing.setPos(relativePosition)

    def _onEntityRemoved(
        self,
        entityId: str
    ):
        item = self.items.pop(entityId, None)

        if item is None:
            return
        
        try:
            self.scene.removeItem(item)
        except Exception:
            pass

    # public methods
    def globalBounds(self) -> QRectF:
        return self.geometry()
    
    def setPlacementCursor(self):
        self.view.setCursor(Qt.CrossCursor)

    def clearPlacementCursor(self):
        try:
            self.view.unsetCursor()
        except Exception:
            pass

    def setEditMode(self, enabled: bool):
        self.inEditMode = enabled

        for item in self.items.values():
            item.setEditMode(enabled)

