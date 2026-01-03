from ..system.sound import SoundCategory, SoundManager
from ..scene.model import DecorationEntity, SceneModel
from ..scene.editor import SceneEditorController

from .flags import InteractabilityFlags, FlagToken

from PySide6.QtCore import QPoint, QPointF, QTimer

from typing import Callable, Optional
from uuid import uuid4

class EventSounds:
    """
    helper for playing event-specific sounds
    """

    def __init__(self, soundManager: SoundManager):
        self._soundManager = soundManager

    def playSound(
        self,
        relativePath: str,
        volume: float = 1.0,
        onFinished: Optional[Callable[[], None]] = None
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
            onFinished=onFinished
        )

class SceneActions:
    """
    helper for performing scene-related actions
    """

    def __init__(self, sprite, sceneSystem):
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

        return list(self.model.entitesList.values())

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
            diffX = entity.position.x() - point.x()
            diffY = entity.position.y() - point.y()

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
        self._sceneModel.removeEntity(entityId)

    def spawnEntity(
        self,
        decorationName: str,
        position: QPointF,
        clampToViewport: bool = True,
        transient: bool = True
    ) -> str:
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
            position=target,
            transient=transient
        )

        self._sceneModel.addEntity(entity)
        return entityId

class EventContext:
    """
    context class provided to event modules
    """
    def __init__(
        self,
        sprite,
        flags: InteractabilityFlags,
        soundManager: SoundManager,
        sceneSystem,
        speechBubble
    ):
        self.sprite = sprite
        self.flags = flags
        self.sounds = EventSounds(soundManager)
        self.scene = SceneActions(sprite, sceneSystem)
        self.sceneSystem = sceneSystem
        self.speech = speechBubble

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