from ..asset import AssetController

from PySide6.QtGui import QGuiApplication, QPainter, QPixmap
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QWidget
)

import random

PUSHOUT_STRENGTH = 0.75
MAX_FALL_TIME = 1.25
RESTITUTION = 0.15

class DecorationItem(QGraphicsPixmapItem):
    def __init__(
        self,
        pixmap: QPixmap,
        terminalVelocity: float = 2.5,
        displayOrder: float = 0.0
    ):
        super().__init__(pixmap)

        self.terminalVelocity = terminalVelocity
        self.velocity = QPointF(0.0, 0.0)
        self.isDragging = False
        self.onGround = False

        self.setZValue(displayOrder)
        self.setShapeMode(QGraphicsPixmapItem.BoundingRectShape)

        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.ItemIsFocusable, False)

        self.setAcceptedMouseButtons(Qt.LeftButton)
    
    def mousePressEvent(self, event):
        self.isDragging = True
        self.velocity = QPointF(0.0, 0.0)
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.isDragging = False
    
    def getBoundingRectInWorld(self) -> QRectF:
        bounds = self.boundingRect()

        return QRectF(
            self.x(),
            self.y(),
            bounds.width(),
            bounds.height()
        )

    def step(self, deltaTime: float, sceneBounds: QRectF, groundY: float):
        if self.isDragging:
            self.onGround = False
            return

        scene = self.scene()

        if scene is None:
            return

        views = scene.views()

        if not views:
            return
        
        controller = views[0].parent()

        if controller is None:
            return

        gravity = controller.calculateGravity()
        maxFallSpeed = controller.calculateMaxFallSpeed(self.terminalVelocity)
        heightRatio = self.y() / max(1.0, sceneBounds.height())

        velocityX = self.velocity.x() * 0.98
        velocityY = min(
            maxFallSpeed,
            self.velocity.y() + gravity * (0.6 + 0.4 * heightRatio) * deltaTime
        )

        self.velocity = QPointF(velocityX, velocityY)

        self.setPos(
            self.pos() + self.velocity * deltaTime
        )

        decorRect = self.boundingRect()

        minX = sceneBounds.left()
        maxX = sceneBounds.right() - decorRect.width()

        if self.x() < minX:
            self.setX(minX)
            self.velocity.setX( -self.velocity.x() * RESTITUTION )
        elif self.x() > maxX:
            self.setX(maxX)
            self.velocity.setX( -self.velocity.x() * RESTITUTION )
        
        bottom = self.y() + decorRect.height()

        if bottom < groundY:
            self.onGround = False
            return
        
        self.onGround = True
        self.setY(
            groundY - decorRect.height()
        )
        
        if abs(self.velocity.y()) > 40.0:
            self.velocity.setY(
                -self.velocity.y() * RESTITUTION
            )
        else:
            self.velocity.setY(0.0)

    def softSeparateColliders(self):
        if self.isDragging:
            return
        
        items = self.collidingItems(Qt.IntersectsItemBoundingRect)

        for collider in items:
            if collider == self:
                continue

            if not isinstance(collider, DecorationItem):
                continue

            a = self.getBoundingRectInWorld()
            b = collider.getBoundingRectInWorld()

            if not a.intersects(b):
                continue

            overlapX = min( a.right(), b.right() ) - max( a.left(), b.left() )
            overlapY = min( a.bottom(), b.bottom() ) - max( a.top(), b.top() )

            if overlapX <= 0.0 or overlapY <= 0.0:
                continue

            if overlapY <= overlapX:
                diff = overlapY * PUSHOUT_STRENGTH

                if a.center().y() < b.center().y():
                    self.setY( self.y() - diff )
                else:
                    self.setY( self.y() + diff )

                self.velocity.setY( self.velocity.y() * (1.0 - PUSHOUT_STRENGTH) )
            else:
                diff = overlapX * PUSHOUT_STRENGTH

                if a.center().x() < b.center().x():
                    self.setX( self.x() - diff )
                else:
                    self.setX( self.x() + diff )

                self.velocity.setX( self.velocity.x() * (1.0 - PUSHOUT_STRENGTH) )

class DecorationScene(QGraphicsScene):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setItemIndexMethod(QGraphicsScene.NoIndex)

class DecorationView(QGraphicsView):
    def __init__(self, parent: QWidget, scene: QGraphicsScene):
        super().__init__(parent)
        self.setScene(scene)

        self.setFrameShape(QGraphicsView.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.setRenderHints(
            QPainter.Antialiasing |
            QPainter.SmoothPixmapTransform
        )

        self.setStyleSheet("background: transparent;")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)

        self.setFocusPolicy(Qt.NoFocus)

class DecorationController(QWidget):
    def __init__(
        self,
        screen,
        refreshRate: int = 10,
        bottomBand: int = 69,
        overlayHeight: int = 0
    ):
        super().__init__(None)

        self.decorationAssets = AssetController("images/decorations")
        self.cachedImages = {}

        self.refreshRate = refreshRate
        self.bottomBand = bottomBand
        self.overlayHeight = overlayHeight

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.NoFocus)

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus
        )

        screenGeometry = screen.geometry()

        overlayHeight = self.overlayHeight

        if (overlayHeight is None) or (overlayHeight <= 0) or (overlayHeight > screenGeometry.height()):
            overlayHeight = screenGeometry.height()

        self.setGeometry(
            screenGeometry.left(),
            screenGeometry.top() + screenGeometry.height() - overlayHeight,
            screenGeometry.width(),
            overlayHeight
        )

        self.scene = DecorationScene(self)
        self.view = DecorationView(self, self.scene)
        self.view.setGeometry(self.rect())

        self.childDecorations: list[DecorationItem] = []
        self.deltaTime = 1.0 / max(1.0, float(refreshRate))

        self.updateTimer = QTimer(self)
        self.updateTimer.timeout.connect(self.stepDecorations)
        self.updateTimer.start(
            max(1, 1000 // refreshRate)
        )

        self._updateSceneBounds()
        self.show()
    
    def _updateSceneBounds(self):
        rect = QRectF(
            0, 0,
            float(self.width()), float(self.height())
        )

        self.scene.setSceneRect(rect)

    def _randPosition(self, decorWidth: int, decorHeight: int) -> QPointF:
        sceneBounds = self.scene.sceneRect()

        x = random.uniform(
            sceneBounds.left(),
            max(sceneBounds.left(), sceneBounds.right() - decorWidth)
        )

        y = random.uniform(
            self.spawnY(),
            max(self.spawnY(), self.floorY() - decorHeight)
        )

        return QPointF(float(x), float(y))

    def resizeEvent(self, event):
        super().resizeEvent(event)

        self.view.setGeometry(self.rect())
        self._updateSceneBounds()

    def floorY(self) -> float:
        return float(self.scene.sceneRect().bottom())
    
    def spawnY(self) -> float:
        return float(self.scene.sceneRect().bottom() - self.bottomBand)

    def calculateGravity(self) -> float:
        sceneHeight = max(1.0, self.scene.sceneRect().height())
        
        return (2.0 * sceneHeight) / (MAX_FALL_TIME ** 2)
    
    def calculateMaxFallSpeed(self, terminalVelocity: float = 1.0) -> float:
        sceneHeight = max(1.0, self.scene.sceneRect().height())
        
        return sceneHeight * terminalVelocity
    
    def addDecoration(
        self,
        pixmap: QPixmap,
        position: QPointF = None,
        initialVelocity: QPointF = QPointF(0.0, 0.0),
    ) -> DecorationItem:
        if pixmap.isNull():
            raise(ValueError("Cannot add decoration with null pixmap"))
        
        decorItem = DecorationItem(pixmap)

        if (position is None) or (position.isNull()):
            position = self._randPosition(
                pixmap.width(),
                pixmap.height()
            )
        
        decorItem.setPos(position)
        decorItem.velocity = initialVelocity

        self.scene.addItem(decorItem)
        self.childDecorations.append(decorItem)
        return decorItem

    def cacheDecorations(self):
        for assetPath in self.decorationAssets.iterateDirectory("", suffixes=(".png", ".jpg", ".jpeg")):
            pixmap = QPixmap( str(assetPath) )

            if pixmap.isNull():
                continue
            
            self.cachedImages[assetPath.stem] = pixmap

    def autoSpawnDecorations(self, count: int = 3):
        if not self.cachedImages:
            self.cacheDecorations()
        
        if not self.cachedImages:
            return
        
        decorations = list(self.cachedImages.keys())

        for _ in range(count):
            decorName = decorations.pop(
                random.randint(0, len(decorations) - 1)
            )
            pixmap = self.cachedImages[decorName]

            self.addDecoration(pixmap)

    def clearDecorations(self):
        for decor in self.childDecorations:
            self.scene.removeItem(decor)
        
        self.childDecorations.clear()

    def stepDecorations(self):
        sceneBounds = self.scene.sceneRect()
        floorY = self.floorY()

        for decor in self.childDecorations:
            decor.step(self.deltaTime, sceneBounds, floorY)
        
        for i in range(2):
            for decor in self.childDecorations:
                decor.softSeparateColliders()

class DecorationSystem:
    def __init__(
        self,
        sprite,
        refreshRate: int = 10,
        bottomBand: int = 69,
        overlayHeight: int = 0
    ):
        self.sprite = sprite
        self.controllers = []

        for screen in QGuiApplication.screens():
            controller = DecorationController(
                screen,
                refreshRate=refreshRate,
                bottomBand=bottomBand,
                overlayHeight=overlayHeight
            )

            controller.autoSpawnDecorations()

            self.controllers.append(controller)
    
    def shutdown(self):
        for controller in self.controllers:
            controller.close()
