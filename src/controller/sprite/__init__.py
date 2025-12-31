from ..system.keyboard import KeyListener
from ..asset import AssetController

from PySide6.QtGui import QPixmap

from dataclasses import dataclass, field
from typing import Callable

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
        and (
            m.keysPerSecond >= 10
            #or (m.averageDelta is not None and m.averageDelta < 0.8)
        ),
    ),
    ReactionRule(
        name="tired_low",
        mood=TIRED_COMBINATION,
        priority=50,
        predicate=lambda m: (m.idleTime < SLEEP_DELTA_THRESHOLD / (3/4))
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
    def __init__(self, _spriteParent, preloadScale: float = None) -> None:
        self.spriteAssets = AssetController("images/sprite")
        self.keyListener = KeyListener()

        self.cachedPixmaps = {
            1.0: PixmapCache()
        }

        self._loadAssets(preloadScale)

    def _loadAssets(self, scale: float = None):
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
        return pixmap.scaled(
            int(pixmap.width() * scale),
            int(pixmap.height() * scale)
        )

    def _loadScaledAsset(
        self,
        scale: float,
        assetType: str,
        name: str = None
    ) -> None:
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
        scale = limitScale(scale)
        self._loadScaledAsset(scale, "body")
        return self.cachedPixmaps[scale].body

    def getFace(self, faceName: str, scale: float = 1.0) -> QPixmap:
        scale = limitScale(scale)
        self._loadScaledAsset(scale, "faces", faceName)

        return self.cachedPixmaps[scale].faces.get(
            faceName,
            QPixmap()
        )
    
    def getEyes(self, eyesName: str, scale: float = 1.0) -> QPixmap:
        scale = limitScale(scale)
        self._loadScaledAsset(scale, "eyes", eyesName)

        return self.cachedPixmaps[scale].eyes.get(
            eyesName,
            QPixmap()
        )
    
    def getHat(self, hatName: str, scale: float = 1.0) -> QPixmap:
        scale = limitScale(scale)
        self._loadScaledAsset(scale, "hats", hatName)

        return self.cachedPixmaps[scale].hats.get(
            hatName,
            QPixmap()
        )

    def chooseMood(
            self,
            timeIdle: float,
            metrics: Metrics = None,
            rules: list[ReactionRule] = EMOTION_DECISION_TABLE
        ) -> tuple[str, str]:
        if metrics is None:
            metrics = Metrics(
                idleTime=timeIdle,
                activityLevel=self.keyListener.getActivityLevel(),
                keysPerSecond=self.keyListener.keysPerSecond(),
                averageDelta=self.keyListener.getAverageDelta()
            )

        logger.debug("metrics=%s", metrics)
        
        # "best" = highest priority rule that matches right now
        for rule in sorted(rules, key=lambda r: r.priority, reverse=True):
            if not rule.predicate(metrics):
                continue

            return rule.mood

        return IDLE_COMBINATION

    def getMoodCombination(self) -> tuple[str, str]:
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
