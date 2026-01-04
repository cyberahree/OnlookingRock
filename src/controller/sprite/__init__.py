from ..system.keyboard import KeyListener
from ..asset import AssetController

from PySide6.QtGui import QPixmap

from dataclasses import dataclass, field
from typing import Callable, Optional

import logging
import time

ASLEEP_COMBINATION = ("idle", "sleepy")
TIRED_COMBINATION = ("idle", "tired")
BLINK_COMBINATION = ("idle", "blink")
DRAG_COMBINATION = ("idle", "dragged")
IDLE_COMBINATION = ("idle", "idle")

SLEEP_DELTA_THRESHOLD = 120
SCALING_LIMITS = (0.1, 2.0)

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class ReactionRule:
    name: str
    mood: tuple[str, str]
    priority: int
    predicate: Callable[[dict], bool]

@dataclass
class Metrics:
    idleTime: float
    activityLevel: float
    keysPerSecond: float
    averageDelta: float

EMOTION_DECISION_TABLE: list[ReactionRule] = [
    ReactionRule(
        name="asleep",
        mood=ASLEEP_COMBINATION,
        priority=100,
        predicate=lambda m: m.idleTime >= SLEEP_DELTA_THRESHOLD,
    ),
    ReactionRule(
        name="tired_idle",
        mood=TIRED_COMBINATION,
        priority=80,
        predicate=lambda m: (SLEEP_DELTA_THRESHOLD / 2) <= m.idleTime < SLEEP_DELTA_THRESHOLD,
    ),
    ReactionRule(
        name="rock",
        mood=("rock", "empty"),
        priority=70,
        predicate=lambda m: (m.idleTime < SLEEP_DELTA_THRESHOLD / 2)
        and (
            m.keysPerSecond >= 13
            or (m.averageDelta is not None and m.averageDelta < 0.04)
        ),
    ),
    ReactionRule(
        name="alert",
        mood=("idle", "alert"),
        priority=60,
        predicate=lambda m: (m.idleTime < SLEEP_DELTA_THRESHOLD / 2)
        and (m.keysPerSecond >= 10),
    ),
    ReactionRule(
        name="tired_low",
        mood=TIRED_COMBINATION,
        priority=50,
        predicate=lambda m: (m.idleTime < SLEEP_DELTA_THRESHOLD / (1/4))
        and (m.activityLevel < 0.15 and m.keysPerSecond < 1.5),
    ),
    ReactionRule(
        name="idle",
        mood=IDLE_COMBINATION,
        priority=0,
        predicate=lambda m: True,
    ),
]

@dataclass
class PixmapCache:
    body: QPixmap = field(default_factory=QPixmap)
    faces: dict[str, QPixmap] = field(default_factory=dict)
    eyes: dict[str, QPixmap] = field(default_factory=dict)
    hats: dict[str, QPixmap] = field(default_factory=dict)

def limitScale(scale: float) -> float:
    return round(
        max(SCALING_LIMITS[0], min(SCALING_LIMITS[1], scale)),
        2
    )

class SpriteSystem:
    """
    manages sprite assets, scaling, and mood selection based on keyboard activity
    """

    def __init__(self, _spriteParent, preloadScale: Optional[float] = None) -> None:
        """
        Initialise the sprite system.
        
        :param _spriteParent: Parent sprite widget
        :param preloadScale: Optional scale to preload at initialization
        :type preloadScale: float
        """

        self.spriteAssets = AssetController("images/sprite")
        self.keyListener = KeyListener()

        self.cachedPixmaps = {
            1.0: PixmapCache()
        }

        self._loadAssets(preloadScale)

    def _loadAssets(self, scale: Optional[float] = None):
        """
        load all sprite assets from disk and cache them.
        
        :param scale: Optional scale to preload additional copies at
        :type scale: float
        """

        loadRescaledCopy = (scale is not None) and (scale != 1.0)

        # load body
        bodyPixmap = QPixmap(self.spriteAssets.getAsset("root.png"))
        self.cachedPixmaps[1.0].body = bodyPixmap

        if loadRescaledCopy:
            scaledBody = self._scalePixmap(bodyPixmap, scale)
            self.cachedPixmaps[scale] = PixmapCache(body=scaledBody)
        
        # load eyes
        for eyeFile in self.spriteAssets.iterateDirectory("eyes", ".png"):
            filePixmap = QPixmap(str(eyeFile))
            self.cachedPixmaps[1.0].eyes[eyeFile.stem] = filePixmap

            if loadRescaledCopy:
                scaledPixmap = self._scalePixmap(filePixmap, scale)
                self.cachedPixmaps[scale].eyes[eyeFile.stem] = scaledPixmap

        # load faces
        for faceFile in self.spriteAssets.iterateDirectory("faces", ".png"):
            filePixmap = QPixmap(str(faceFile))
            self.cachedPixmaps[1.0].faces[faceFile.stem] = filePixmap

            if loadRescaledCopy:
                scaledPixmap = self._scalePixmap(filePixmap, scale)
                self.cachedPixmaps[scale].faces[faceFile.stem] = scaledPixmap
        
        # load hats
        for hatFile in self.spriteAssets.iterateDirectory("hats", ".png"):
            filePixmap = QPixmap(str(hatFile))
            self.cachedPixmaps[1.0].hats[hatFile.stem] = filePixmap

            if loadRescaledCopy:
                scaledPixmap = self._scalePixmap(filePixmap, scale)
                self.cachedPixmaps[scale].hats[hatFile.stem] = scaledPixmap

    def _scalePixmap(self, pixmap: QPixmap, scale: float) -> QPixmap:
        """
        scale a pixmap to a new size.
        
        :param pixmap: The pixmap to scale
        :type pixmap: QPixmap
        :param scale: Scale factor to apply
        :type scale: float
        :return: The scaled pixmap
        :rtype: QPixmap
        """

        return pixmap.scaled(
            int(pixmap.width() * scale),
            int(pixmap.height() * scale)
        )

    def _loadScaledAsset(
        self,
        scale: float,
        assetType: str,
        name: Optional[str] = None
    ) -> None:
        """
        load and cache a scaled copy of an asset.
        
        :param scale: Scale factor to load at
        :type scale: float
        :param assetType: Type of asset (body, faces, eyes, hats)
        :type assetType: str
        :param name: Name of the asset (required for non-body types)
        :type name: str
        """

        scale = limitScale(scale)

        if not scale in self.cachedPixmaps:
            self.cachedPixmaps[scale] = PixmapCache()
        else:
            # check if already cached
            if assetType == "body":
                if not self.cachedPixmaps[scale].body.isNull():
                    return
            else:
                cachedCollection = getattr(self.cachedPixmaps[scale], assetType)
                if name in cachedCollection:
                    return

        # get the full-scale pixmap
        fullPixmap = None

        if assetType == "body":
            fullPixmap = self.cachedPixmaps[1.0].body
        else:
            fullPixmap = getattr(
                self.cachedPixmaps[1.0],
                assetType
            ).get(name, None)
        
        if fullPixmap is None:
            raise ValueError(f"Asset {assetType}/{name} not found for scaling")
        
        # scale it
        scaledPixmap = fullPixmap.scaled(
            int(fullPixmap.width() * scale),
            int(fullPixmap.height() * scale)
        )

        # cache it
        if assetType == "body":
            self.cachedPixmaps[scale].body = scaledPixmap
        else:
            getattr(
                self.cachedPixmaps[scale],
                assetType
            )[name] = scaledPixmap

    def getBody(self, scale: float = 1.0) -> QPixmap:
        """
        get the body pixmap at the specified scale.
        
        :param scale: Scale factor, defaults to 1.0
        :type scale: float
        :return: The body pixmap
        :rtype: QPixmap
        """

        scale = limitScale(scale)
        self._loadScaledAsset(scale, "body")

        return self.cachedPixmaps[scale].body

    def getFace(self, faceName: str, scale: float = 1.0) -> QPixmap:
        """
        get a face pixmap by name at the specified scale.
        
        :param faceName: Name of the face to retrieve
        :type faceName: str
        :param scale: Scale factor, defaults to 1.0
        :type scale: float
        :return: The face pixmap
        :rtype: QPixmap
        """

        scale = limitScale(scale)
        self._loadScaledAsset(scale, "faces", faceName)

        return self.cachedPixmaps[scale].faces.get(
            faceName,
            QPixmap()
        )
    
    def getEyes(self, eyesName: str, scale: float = 1.0) -> QPixmap:
        """
        get an eyes pixmap by name at the specified scale.
        
        :param eyesName: Name of the eyes to retrieve
        :type eyesName: str
        :param scale: Scale factor, defaults to 1.0
        :type scale: float
        :return: The eyes pixmap
        :rtype: QPixmap
        """

        scale = limitScale(scale)
        self._loadScaledAsset(scale, "eyes", eyesName)

        return self.cachedPixmaps[scale].eyes.get(
            eyesName,
            QPixmap()
        )
    
    def getHat(self, hatName: str, scale: float = 1.0) -> QPixmap:
        """
        get a hat pixmap by name at the specified scale.
        
        :param hatName: Name of the hat to retrieve
        :type hatName: str
        :param scale: Scale factor, defaults to 1.0
        :type scale: float
        :return: The hat pixmap
        :rtype: QPixmap
        """

        scale = limitScale(scale)
        self._loadScaledAsset(scale, "hats", hatName)

        return self.cachedPixmaps[scale].hats.get(
            hatName,
            QPixmap()
        )

    def chooseMood(
        self,
        timeIdle: float,
        metrics: Optional[Metrics] = None,
        rules: list[ReactionRule] = EMOTION_DECISION_TABLE
    ) -> tuple[str, str]:
        """
        choose a mood based on metrics and reaction rules.
        
        :param timeIdle: Time idle in seconds
        :type timeIdle: float
        :param metrics: Activity metrics, defaults to current keyboard metrics
        :type metrics: Metrics
        :param rules: Emotion decision rules to evaluate, defaults to standard table
        :type rules: list[ReactionRule]
        :return: Tuple of (body_mood, face_mood)
        :rtype: tuple[str, str]
        """

        if metrics is None:
            metrics = Metrics(
                idleTime=timeIdle,
                activityLevel=self.keyListener.getActivityLevel(),
                keysPerSecond=self.keyListener.keysPerSecond(),
                averageDelta=self.keyListener.getAverageDelta()
            )

        # TODO: uncomment
        #logger.debug("metrics=%s", metrics)
        
        # "best" = highest priority rule that matches right now
        for rule in sorted(rules, key=lambda r: r.priority, reverse=True):
            if not rule.predicate(metrics):
                continue

            return rule.mood

        return IDLE_COMBINATION

    def getMoodCombination(self) -> tuple[str, str]:
        """
        get the current mood combination based on idle time and activity.
        
        :return: Tuple of (body_mood, face_mood)
        :rtype: tuple[str, str]
        """

        if self.keyListener.lastKeyPress is None:
            return IDLE_COMBINATION
        
        idle = time.time() - self.keyListener.lastKeyPress

        # no activity = asleep
        # factz
        if idle >= SLEEP_DELTA_THRESHOLD:
            return ASLEEP_COMBINATION

        # tired mode
        if idle >= (SLEEP_DELTA_THRESHOLD / 3):
            return TIRED_COMBINATION
    
        return self.chooseMood(idle)
