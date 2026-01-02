from .model import DecorationEntity, SceneModel
from .editor import SceneEditorController
from .items import DecorationGraphicsItem

from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QWidget, QGraphicsPixmapItem
from PySide6.QtCore import QPointF, QRectF, Qt, QPoint
from PySide6.QtGui import QPainter, QPixmap, QScreen

from typing import Dict

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

        # enable hover/move events without holding a button
        self.setMouseTracking(True)

        try:
            self.viewport().setMouseTracking(True)
        except Exception:
            pass

        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setFocusPolicy(Qt.NoFocus)

        # needed so we can show the placement ghost while just moving the mouse
        self.setMouseTracking(True)

        try:
            self.viewport().setMouseTracking(True)
        except Exception:
            pass

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
        self.placementActive = False

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.NoFocus)

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus
        )

        self.setGeometry(
            self.screen.geometry()
        )

        self.scene = DecorationScene(self)

        self.ghost = QGraphicsPixmapItem()
        self.ghost.setOpacity(0.55)
        self.ghost.setVisible(False)
        self.ghost.setZValue(999000)
        self.ghost.setAcceptedMouseButtons(Qt.NoButton)
        self.scene.addItem(self.ghost)

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

        try:
            self.updateMouseInputAttributes()
        except Exception:
            pass

        self.updateMouseInputAttributes()

        self.model.entityAdded.connect(self._onEntityChanged)
        self.model.entityUpdated.connect(self._onEntityChanged)
        self.model.entityRemoved.connect(self._onEntityRemoved)

        # TODO: implement physics
        clock.timer.timeout.connect(lambda: None)

    # events
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.view.setGeometry(self.rect())
        self.updateSceneBounds()

    # internal methods
    def updateSceneBounds(self):
        self.scene.setSceneRect(
            QRectF(
                0, 0,
                self.width(),
                self.height()
            )
        )
    
    def _viewportOriginalGlobal(self) -> QPointF:
        geometry = self.geometry()

        return QPointF(
            float(geometry.left()),
            float(geometry.top())
        )

    def _shouldContain(
        self,
        entity: DecorationEntity,
        pixmap: QPixmap
    ) -> bool:
        width = pixmap.width()
        height = pixmap.height()
        
        centre = QPointF(
            entity.x + width / 2.0,
            entity.y + height / 2.0
        ) 

        return self.globalBounds().contains(
            centre.x(), centre.y()
        )
    
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
        # for this overlay, geometry() is in global desktop coordinates.
        geometry = self.geometry()

        return QRectF(
            float(geometry.left()),
            float(geometry.top()),
            float(geometry.width()),
            float(geometry.height())
        )

    def setGhostDecoration(self, name: str):
        try:
            pixmap = self.decorationPixmapProvider(name)
        except:
            pixmap = None

        if (pixmap is None) or (pixmap.isNull()):
            self.clearGhost()
            return
        
        # only update if different
        try:
            if self.ghost.pixmap().cacheKey() != pixmap.cacheKey():
                self.ghost.setPixmap(pixmap)
        except Exception:
            self.ghost.setPixmap(pixmap)

    def showGhostAt(self, globalTopLeftPosition: QPointF, name: str):
        self.setGhostDecoration(name)

        if self.ghost.pixmap().isNull():
            return
        
        origin = self._viewportOriginalGlobal()
        relative = QPointF(
            globalTopLeftPosition.x() - origin.x(),
            globalTopLeftPosition.y() - origin.y()
        )

        self.ghost.setPos(relative)
        self.ghost.setVisible(True)

    def clearGhost(self):
        try:
            self.ghost.setVisible(False)
            self.ghost.setPixmap(QPixmap())
        except Exception:
            pass

    def _applyInputMode(self, interactive: bool) -> None:
        transparent = not bool(interactive)

        # qt-level (widget) event handling
        try:
            self.setAttribute(Qt.WA_TransparentForMouseEvents, transparent)
        except Exception:
            pass

        try:
            self.view.setAttribute(Qt.WA_TransparentForMouseEvents, transparent)
            self.view.viewport().setAttribute(Qt.WA_TransparentForMouseEvents, transparent)
        except Exception:
            pass

        # os-level input transparency for true click-through on many platforms
        try:
            flags = self.windowFlags()

            if transparent:
                flags |= Qt.WindowTransparentForInput
            else:
                flags &= ~Qt.WindowTransparentForInput

            self.setWindowFlags(flags)

            # re-apply geometry because setWindowFlags can reset it on some platforms
            try:
                self.setGeometry(self.screen.geometry())
            except Exception:
                pass

            self.show()
            self.raise_()
        except Exception:
            pass

        # after any flag/geometry changes, ensure items are positioned correctly
        try:
            origin = self._viewportOriginalGlobal()

            for entity in self.model.entitesList.values():
                item = self.items.get(entity.entityId)

                if item is None:
                    continue

                item.setPos(
                    QPointF(
                        entity.x - origin.x(),
                        entity.y - origin.y()
                    )
                )
        except Exception:
            pass

    def updateMouseInputAttributes(self):
        self._applyInputMode(self.inEditMode or self.placementActive)

    def setPlacementCursor(self):
        # placement needs mouse input even if edit mode is off
        self.placementActive = True
        self._applyInputMode(self.inEditMode or self.placementActive)

        try:
            self.view.setCursor(Qt.CrossCursor)
        except Exception:
            pass

    def clearPlacementCursor(self):
        self.placementActive = False

        try:
            self.view.unsetCursor()
        except Exception:
            pass

        self.updateMouseInputAttributes()

    def setEditMode(self, enabled: bool):
        self.inEditMode = enabled
        self.updateMouseInputAttributes()

        for item in self.items.values():
            item.setEditMode(enabled)
