from ..asset import AssetController

from .persistence import ScenePersistence
from .viewport import SceneViewportWindow
from .editor import SceneEditorController
from .layout import ScreenLayoutHandler
from .model import SceneModel

from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtCore import QPoint, QPointF

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

        for screen in self.config.getScreens():
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
    
    def shutdown(self):
        for viewport in self.viewports:
            try:
                viewport.close()
            except Exception:
                pass

    # assets methods
    def listDecorations(self) -> list[str]:
        return sorted(
            [decoration.stem for decoration in self.assets.listAssets()]
        )

    def getDecorationPixmap(self, name: str) -> QPixmap:
        if name in self.assetsCache:
            return self.assetsCache[name]
        
        path = self.assets.blindGetAsset(name)
        pixmap = QPixmap(path) if path is not None else QPixmap()

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
            point = QPoint(
                int(globalPoint.x()),
                int(globalPoint.y())
            )
        except Exception:
            point = QPoint(0, 0)

        # prefer qt screen mapping
        try:
            screen = QGuiApplication.screenAt(point)
        except Exception:
            screen = None

        if screen is not None:
            screenName = getattr(screen, 'name', lambda: '')()

            for viewport in self.viewports:
                if viewport.screen.name != screenName:
                    continue

                return viewport

        for viewport in self.viewports:
            if viewport.screen.boundsGlobal.contains(point):
                return viewport
        
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
        self.editor.beginPlacement(decorationName)

        for viewport in self.viewports:
            viewport.setPlacementCursor(decorationName)
    
    def endPlacement(self) -> None:
        self.editor.emptyPlacement()

        for viewport in self.viewports:
            viewport.clearPlacementCursor()
