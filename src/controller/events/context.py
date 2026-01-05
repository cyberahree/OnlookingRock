from ..interfaces.windows.mediaview import MediaViewWindow

from ..system.sound import SoundCategory, SoundManager
from ..scene.model import DecorationEntity, SceneModel
from ..scene.editor import SceneEditorController

from .flags import InteractabilityFlags, FlagToken

from PySide6.QtCore import QPoint, QPointF, QTimer, QPropertyAnimation, QEasingCurve, QEventLoop
from PySide6.QtGui import QGuiApplication

from typing import Callable, Optional
from uuid import uuid4

class EventSounds:
    """
    helper for playing event-specific sounds

    :param soundManager: sound manager instance
    :type soundManager: SoundManager
    """

    def __init__(self, soundManager: SoundManager):
        """
        initialise the event sounds helper
        
        :param soundManager: sound manager instance
        :type soundManager: SoundManager
        """
        self._soundManager = soundManager

    def playSound(
        self,
        relativePath: str,
        volume: float = 1.0,
        onFinish: Optional[Callable[[], None]] = None
    ):
        """
        play a sound effect

        :param relativePath: relative path of the sound file
        :type relativePath: str
        :param volume: volume multiplier
        :type volume: float
        :param onFinished: callback when finished
        :type onFinished: Optional[Callable[[], None]]
        """

        return self._soundManager.playSound(
            relativePath,
            SoundCategory.EVENT,
            volume=volume,
            onFinish=onFinish
        )

class SceneActions:
    """
    helper for performing scene-related actions

    :param sprite: the sprite instance
    :type sprite: SpriteWidget
    :param sceneSystem: scene system instance
    :type sceneSystem: SceneSystem
    """

    def __init__(self, sprite, sceneSystem):
        """
        initialise the scene actions helper
        
        :param sprite: the sprite instance
        :type sprite: SpriteWidget
        :param sceneSystem: scene system instance
        :type sceneSystem: SceneSystem
        """
        self._sprite = sprite
        self._sceneSystem = sceneSystem
        self._sceneEditor: SceneEditorController = sceneSystem.editor
        self._sceneModel: SceneModel = sceneSystem.model

    def getSpriteCentre(self) -> QPointF:
        """
        get the sprite's centre position in scene coordinates

        :return: sprite centre position
        :rtype: QPointF
        """

        spriteCentre = self._sprite.mapToGlobal(
            QPoint(
                self._sprite.width() // 2,
                self._sprite.height() // 2
            )
        )

        return QPointF(
            float(spriteCentre.x()),
            float(spriteCentre.y())
        )

    def getEntities(self) -> list[DecorationEntity]:
        """
        get all scene entities

        :return: list of scene entities
        :rtype: List[SceneEntity]
        """

        return list(self._sceneModel.entitesList.values())

    def findEntitiesByName(self, name: str) -> list[DecorationEntity]:
        """
        find a scene entity by name

        :param name: entity name
        :type name: str
        :return: scene entity or None if not found
        :rtype: Optional[SceneEntity]
        """

        return [
            entity for entity in self.getEntities()
            if entity.name == name
        ]

    def getNearestEntityFromPoint(
        self,
        point: QPointF,
        maxDistance: float = 10**18
    ) -> Optional[DecorationEntity]:
        """
        get the nearest scene entity from a point

        :param point: reference point
        :type point: QPointF
        :param maxDistance: maximum distance to consider
        :type maxDistance: float
        :return: nearest scene entity or None if not found
        :rtype: Optional[SceneEntity]
        """
        bestDistance = maxDistance
        bestEntity = None

        for entity in self.getEntities():
            diffX = entity.x - point.x()
            diffY = entity.y - point.y()

            distance = (diffX ** 2 + diffY ** 2) ** 0.5

            if distance < bestDistance:
                bestDistance = distance
                bestEntity = entity

        return bestEntity

    def moveEntity(
        self,
        entityId: str,
        position: QPointF,
        clampToViewport: bool = True
    ):
        """
        Move a scene entity to a new position.

        :param entityId: ID of the entity to move
        :type entityId: str
        :param position: New position for the entity
        :type position: QPointF
        :param clampToViewport: Whether to clamp the position to viewport bounds
        :type clampToViewport: bool
        """
        entity = self._sceneModel.getEntity(entityId)

        if entity is None:
            return

        target = position

        if clampToViewport:
            target = self._sceneEditor.clampToViewport(
                target,
                entity.name
            )

        self._sceneModel.updateEntity(
            entityId,
            position=target
        )

    def removeEntity(self, entityId: str):
        """
        Remove an entity from the scene.

        :param entityId: ID of the entity to remove
        :type entityId: str
        """
        self._sceneModel.removeEntity(entityId)

    def spawnEntity(
        self,
        decorationName: str,
        position: QPointF,
        clampToViewport: bool = True,
        transient: bool = True
    ) -> str:
        """
        Spawn a new decoration entity in the scene.

        :param decorationName: Name of the decoration to spawn
        :type decorationName: str
        :param position: Position to spawn the entity at
        :type position: QPointF
        :param clampToViewport: Whether to clamp the position to viewport bounds
        :type clampToViewport: bool
        :param transient: Whether the entity should be transient (not persisted)
        :type transient: bool
        :return: The ID of the newly spawned entity
        :rtype: str
        """
        target = position

        if clampToViewport:
            target = self._sceneEditor.clampToViewport(
                target,
                decorationName
            )

        entityId = str(uuid4())

        entity = DecorationEntity(
            entityId=entityId,
            name=decorationName,
            x=target.x(),
            y=target.y(),
            transient=transient
        )

        self._sceneModel.addEntity(entity)
        return entityId

class EventContext:
    """
    context class provided to event modules

    :param sprite: the sprite instance
    :type sprite: SpriteWidget
    :param flags: interactability flags manager
    :type flags: InteractabilityFlags
    :param soundManager: sound manager instance
    :type soundManager: SoundManager
    :param sceneSystem: scene system instance
    :type sceneSystem: SceneSystem
    :param mediaView: media view window instance
    :type mediaView: MediaViewWindow
    :param speechBubble: speech bubble controller
    :type speechBubble: SpeechBubbleController
    """
    def __init__(
        self,
        sprite,
        flags: InteractabilityFlags,
        soundManager: SoundManager,
        sceneSystem,
        mediaView: MediaViewWindow,
        speechBubble
    ):
        """
        initialise the event context
        
        :param flags: interactability flags manager
        :type flags: InteractabilityFlags
        :param soundManager: sound manager instance
        :type soundManager: SoundManager
        :param sceneSystem: scene system instance
        :param mediaView: media view window instance
        :type mediaView: MediaViewWindow
        :param speechBubble: speech bubble controller
        """
        self.sprite = sprite
        self.flags = flags
        self.sounds = EventSounds(soundManager)
        self.scene = SceneActions(sprite, sceneSystem)
        self.sceneSystem = sceneSystem
        self.speech = speechBubble
        self.mediaView = mediaView
        self._spriteMoveAnimation: Optional[QPropertyAnimation] = None

    def lock(
        self,
        owner: str,
        *flags: str,
    ) -> FlagToken:
        """
        lock interactability flags for the sprite
        
        :param owner: owner of the lock
        :type owner: str
        :param flags: flags to lock
        :type flags: str
        :return: token representing the lock
        :rtype: FlagToken
        """

        return self.flags.acquire(owner, flags)

    def delayMs(self, milliseconds: int, callback: Callable[[], None]):
        """
        delay execution of a callback by a number of milliseconds
        
        :param milliseconds: delay duration in milliseconds
        :type milliseconds: int
        :param callback: callback to execute after delay
        :type callback: Callable[[], None]
        :return: QTimer instance managing the delay
        :rtype: QTimer
        """

        QTimer.singleShot(
            max(0, int(milliseconds)),
            callback
        )

    def yieldMs(self, milliseconds: int):
        """
        block execution for a number of milliseconds, processing Qt events

        :param milliseconds: yield duration in milliseconds
        :type milliseconds: int
        """
        if milliseconds <= 0:
            return

        loop = QEventLoop()
        QTimer.singleShot(max(1, int(milliseconds)), loop.quit)
        loop.exec()

    def animateSpriteTo(
        self,
        target: QPointF,
        durationMs: int = 400,
        clampToScreen: bool = True,
        easing: QEasingCurve.Type = QEasingCurve.OutCubic,
        onFinished: Optional[Callable[[], None]] = None
    ) -> QPropertyAnimation:
        """
        Smoothly move the sprite to a target point with optional screen clamping.

        :param target: Destination centre point in global coordinates
        :param durationMs: Duration of the animation in milliseconds
        :param clampToScreen: Whether to clamp the destination to the current screen
        :param easing: Easing curve for the animation
        :param onFinished: Optional callback when animation completes
        :return: The QPropertyAnimation instance managing the move
        """

        point = QPointF(target)  # desired centre position

        halfWidth = self.sprite.width() / 2.0
        halfHeight = self.sprite.height() / 2.0

        # translate centre target to top-left for positioning
        topLeft = QPointF(point.x() - halfWidth, point.y() - halfHeight)

        if clampToScreen:
            # clamp using the target point's screen, not the sprite's current screen
            screen = QGuiApplication.screenAt(point.toPoint())

            if screen is None:
                screen = QGuiApplication.primaryScreen()

            if screen is not None:
                bounds = screen.availableGeometry()

                clampedX = max(
                    bounds.left(),
                    min(int(topLeft.x()), bounds.right() - self.sprite.width())
                )

                clampedY = max(
                    bounds.top(),
                    min(int(topLeft.y()), bounds.bottom() - self.sprite.height())
                )

                topLeft = QPointF(float(clampedX), float(clampedY))

        destination = QPoint(int(topLeft.x()), int(topLeft.y()))

        if self._spriteMoveAnimation is not None:
            try:
                self._spriteMoveAnimation.stop()
            except Exception:
                pass

        moveAnimation = QPropertyAnimation(self.sprite, b"pos", self.sprite)
        moveAnimation.setDuration(max(1, int(durationMs)))
        moveAnimation.setStartValue(self.sprite.pos())
        moveAnimation.setEndValue(destination)
        moveAnimation.setEasingCurve(easing)

        if onFinished is not None:
            moveAnimation.finished.connect(onFinished)

        self._spriteMoveAnimation = moveAnimation
        moveAnimation.start()

        return moveAnimation