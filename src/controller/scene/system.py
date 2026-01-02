from ..asset import AssetController

from .persistence import ScenePersistence
from .viewport import SceneViewportWindow
from .editor import SceneEditorController
from .layout import ScreenLayoutHandler
from .model import SceneModel

from PySide6.QtGui import QGuiApplication, QPixmap, QCursor
from PySide6.QtCore import QPoint, QPointF, QTimer

from typing import Dict

class SceneSystem:
    def __init__(
        self,
        sprite,
        clock=None
    ):
        self.sprite = sprite
        self.config = self.sprite.config
        self.clock = clock

        self.layout = ScreenLayoutHandler()
        self.model = SceneModel(sprite)

        self.assets = AssetController("images/decorations")
        self.assetsCache: Dict[str, QPixmap] = {}

        # editor needs to know how big the decoration is, and which viewport is under a point
        self.editor = SceneEditorController(
            self, sprite
        )

        # viewport management
        self.viewports: list[SceneViewportWindow] = []

        for screen in QGuiApplication.screens():
            viewportController = SceneViewportWindow(
                screen=screen,
                clock=self.clock,
                model=self.model,
                editor=self.editor,
                system=self
            )

            self.viewports.append(viewportController)
        
        # persistence
        self.persistence = ScenePersistence(
            self.model,
            self.config,
            self.layout,
            sprite
        )

        self.persistence.loadOrSpawn()

        # ensure viewports mirror current model immediately
        for entity in self.model.entitesList.values():
            self.model.entityUpdated.emit(entity)

        # ghost preview updates should not depend on mouse-move delivery
        # some platforms won't deliver move events to non-activating tool windows
        self._ghostTimer = QTimer(self.sprite)
        self._ghostTimer.setInterval(33)
        self._ghostTimer.timeout.connect(self._tickGhost)
    
    def shutdown(self):
        for viewport in self.viewports:
            try:
                viewport.close()
            except Exception:
                pass

    # assets methods
    def listDecorations(self) -> list[str]:
        return sorted([p.stem for p in self.assets.listDirectory("")])

    def getDecorationPixmap(self, name: str) -> QPixmap:
        if name in self.assetsCache:
            return self.assetsCache[name]
        
        path = self.assets.blindGetAsset(name)
        pixmap = QPixmap(str(path)) if path is not None else QPixmap()

        self.assetsCache[name] = pixmap
        return pixmap

    def getDecorationSize(self, name: str) -> tuple[int, int]:
        pixmap = self.getDecorationPixmap(name)

        if (pixmap is None) or pixmap.isNull():
            return (32, 32)

        return (pixmap.width(), pixmap.height())

    # viewport methods
    def getViewportAtPoint(self, globalPoint: QPointF):
        try:
            pointX = float(globalPoint.x())
            pointY = float(globalPoint.y())
        except Exception:
            pointX, pointY = 0.0, 0.0

        # 1) explicit bounds check
        for viewport in self.viewports:
            try:
                if viewport.globalBounds().contains(pointX, pointY):
                    return viewport
            except Exception:
                pass

        # 2) fallback: Qt screen mapping
        try:
            point = QPoint(int(pointX), int(pointY))
            screen = QGuiApplication.screenAt(point)
        except Exception:
            screen = None

        if screen is not None:
            try:
                screenName = screen.name()
            except Exception:
                screenName = ""

            for viewport in self.viewports:
                try:
                    if viewport.screen.name() == screenName:
                        return viewport
                except Exception:
                    pass

        return self.viewports[0] if self.viewports else None
    
    def getSpriteViewport(self) -> SceneViewportWindow:
        try:
            centre = self.sprite.mapToGlobal(
                QPoint(
                    self.sprite.width() // 2,
                    self.sprite.height() // 2
                )
            )

            return self.getViewportAtPoint(
                QPointF(
                    float(centre.x()),
                    float(centre.y())
                )
            )
        except Exception:
            return self.viewports[0] if self.viewports else None

    # ui-specific methods
    def setEditMode(self, enabled: bool) -> None:
        self.editor.setEditing(enabled)

        for viewport in self.viewports:
            viewport.setEditMode(enabled)
    
    def beginPlacement(
        self,
        decorationName: str
    ) -> None:
        # placement implies edit-capable interaction.
        if not self.editor.canEdit:
            self.setEditMode(True)

        self.editor.beginPlacement(decorationName)

        for viewport in self.viewports:
            viewport.setPlacementCursor()

        # start continuous ghost updates
        try:
            self._ghostTimer.start()
        except Exception:
            pass

        # show ghost immediately (no need to move the mouse)
        try:
            self._tickGhost()
        except Exception:
            pass

    def endPlacement(self) -> None:
        self.editor.emptyPlacement()

        try:
            self._ghostTimer.stop()
        except Exception:
            pass

        for viewport in self.viewports:
            viewport.clearPlacementCursor()
            viewport.clearGhost()

    def _tickGhost(self) -> None:
        name = getattr(self.editor, "placementName", None)

        if not name:
            # no placement active
            for viewport in self.viewports:
                try:
                    viewport.clearGhost()
                except Exception:
                    pass
            return

        try:
            cursorPosition = QCursor.pos()

            cursorPos = QPointF(
                float(cursorPosition.x()),
                float(cursorPosition.y())
            )
        except Exception:
            return

        targetViewport = self.getViewportAtPoint(cursorPos)

        if targetViewport is None:
            return

        width, height = self.getDecorationSize(str(name))
        bounds = targetViewport.globalBounds()

        target = QPointF(
            cursorPos.x() - width / 2.0,
            cursorPos.y() - height / 2.0
        )

        clampedX = max(bounds.left(), min(bounds.right() - width, target.x()))
        clampedY = max(bounds.top(), min(bounds.bottom() - height, target.y()))
        clamped = QPointF(clampedX, clampedY)

        for viewport in self.viewports:
            if viewport is targetViewport:
                continue
            try:
                viewport.clearGhost()
            except Exception:
                pass

        try:
            targetViewport.showGhostAt(clamped, str(name))
        except Exception:
            pass
