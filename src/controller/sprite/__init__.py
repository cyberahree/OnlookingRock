from ..system.keyboard import KeyListener
from ..asset import AssetController

from PySide6.QtGui import QPixmap

from dataclasses import dataclass, field
from typing import Callable

import time

ASLEEP_COMBINATION = ("idle", "sleepy")
TIRED_COMBINATION = ("idle", "tired")
BLINK_COMBINATION = ("idle", "blink")
DRAG_COMBINATION = ("idle", "dragged")
IDLE_COMBINATION = ("idle", "idle")

SLEEP_DELTA_THRESHOLD = 120

@dataclass(frozen=True)
class ReactionRule:
    name: str
    mood: tuple[str, str]
    priority: int
    predicate: Callable[[dict], bool]

@dataclass
class Metrics:
    IDLE_TIME: float
    ACTIVITY_LEVEL: float
    KEYS_PER_SECOND: float
    AVERAGE_DELTA: float

EMOTION_DECISION_TABLE: list[ReactionRule] = [
    ReactionRule(
        name="asleep",
        mood=ASLEEP_COMBINATION,
        priority=100,
        predicate=lambda m: m.IDLE_TIME >= SLEEP_DELTA_THRESHOLD,
    ),
    ReactionRule(
        name="tired_idle",
        mood=TIRED_COMBINATION,
        priority=80,
        predicate=lambda m: (SLEEP_DELTA_THRESHOLD / 2) <= m.IDLE_TIME < SLEEP_DELTA_THRESHOLD,
    ),
    ReactionRule(
        name="rock",
        mood=("rock", "empty"),
        priority=70,
        predicate=lambda m: (m.IDLE_TIME < SLEEP_DELTA_THRESHOLD / 2)
        and (
            m.KEYS_PER_SECOND >= 13
            or (m.AVERAGE_DELTA is not None and m.AVERAGE_DELTA < 0.04)
        ),
    ),
    ReactionRule(
        name="alert",
        mood=("idle", "alert"),
        priority=60,
        predicate=lambda m: (m.IDLE_TIME < SLEEP_DELTA_THRESHOLD / 2)
        and (
            m.KEYS_PER_SECOND >= 10
            #or (m.AVERAGE_DELTA is not None and m.AVERAGE_DELTA < 0.8)
        ),
    ),
    ReactionRule(
        name="tired_low",
        mood=TIRED_COMBINATION,
        priority=50,
        predicate=lambda m: (m.IDLE_TIME < SLEEP_DELTA_THRESHOLD / 2)
        and (m.ACTIVITY_LEVEL < 0.15 and m.KEYS_PER_SECOND < 1.5),
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
    Body: QPixmap = field(default_factory=QPixmap)
    Faces: dict[str, QPixmap] = field(default_factory=dict)
    Eyes: dict[str, QPixmap] = field(default_factory=dict)

class SpriteSystem:
    def __init__(self, _spriteParent, preloadScale: float = None) -> None:
        self.SpriteAssets = AssetController("images/sprite")
        self.KeyListener = KeyListener()

        self.cachedPixmaps = {
            1.0: PixmapCache()
        }

        self._loadAssets(preloadScale)

    def _loadAssets(self, scale: float = None):
        loadRescaledCopy = (scale is not None) and (scale != 1.0)

        # load body
        bodyPixmap = QPixmap(self.SpriteAssets.getAsset("root.png"))
        self.cachedPixmaps[1.0].Body = bodyPixmap

        if loadRescaledCopy:
            scaledBody = self._scalePixmap(bodyPixmap, scale)
            self.cachedPixmaps[scale] = PixmapCache(Body=scaledBody)
        
        # load eyes
        for eyeFile in self.SpriteAssets.iterateDirectory("eyes", ".png"):
            filePixmap = QPixmap(str(eyeFile))
            self.cachedPixmaps[1.0].Eyes[eyeFile.stem] = filePixmap

            if loadRescaledCopy:
                scaledPixmap = self._scalePixmap(filePixmap, scale)
                self.cachedPixmaps[scale].Eyes[eyeFile.stem] = scaledPixmap

        # load faces
        for faceFile in self.SpriteAssets.iterateDirectory("faces", ".png"):
            filePixmap = QPixmap(str(faceFile))
            self.cachedPixmaps[1.0].Faces[faceFile.stem] = filePixmap

            if loadRescaledCopy:
                scaledPixmap = self._scalePixmap(filePixmap, scale)
                self.cachedPixmaps[scale].Faces[faceFile.stem] = scaledPixmap
    
    def _scalePixmap(self, pixmap: QPixmap, scale: float) -> QPixmap:
        return pixmap.scaled(
            pixmap.width() * scale,
            pixmap.height() * scale
        )

    def _loadScaledAsset(
        self,
        scale: float,
        type: str,
        name: str = None
    ) -> None:
        if not scale in self.cachedPixmaps:
            self.cachedPixmaps[scale] = PixmapCache()
        else:
            # check if already cached
            if type == "body":
                if not self.cachedPixmaps[scale].Body.isNull():
                    return
            else:
                if name in self.cachedPixmaps[scale].__dict__[type.capitalize()]:
                    return

        # get the full-scale pixmap
        fullPixmap = None

        if type == "body":
            fullPixmap = self.cachedPixmaps[1.0].Body
        else:
            fullPixmap = getattr(
                self.cachedPixmaps[1.0],
                type.capitalize()
            ).get(name, None)
        
        if fullPixmap is None:
            raise ValueError(f"Asset {type}/{name} not found for scaling")
        
        # scale it
        scaledPixmap = fullPixmap.scaled(
            fullPixmap.width() * scale,
            fullPixmap.height() * scale
        )

        # cache it
        if type == "body":
            self.cachedPixmaps[scale].Body = scaledPixmap
        else:
            getattr(
                self.cachedPixmaps[scale],
                type.capitalize()
            )[name] = scaledPixmap

    def getBody(self, scale: float = 1.0) -> QPixmap:
        scale = max(0.1, scale)
        self._loadScaledAsset(scale, "body")

        return self.cachedPixmaps[scale].Body

    def getFace(self, faceName: str, scale: float = 1.0) -> QPixmap:
        scale = max(0.1, scale)
        self._loadScaledAsset(scale, "faces", faceName)

        return self.cachedPixmaps[scale].Faces.get(
            faceName,
            QPixmap()
        )
    
    def getEyes(self, eyesName: str, scale: float = 1.0) -> QPixmap:
        scale = max(0.1, scale)
        self._loadScaledAsset(scale, "eyes", eyesName)

        return self.cachedPixmaps[scale].Eyes.get(
            eyesName,
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
                IDLE_TIME = timeIdle,
                ACTIVITY_LEVEL = self.KeyListener.getActivityLevel(),
                KEYS_PER_SECOND = self.KeyListener.keysPerSecond(),
                AVERAGE_DELTA = self.KeyListener.getAverageDelta()
            )

        print(metrics)
        
        # "best" = highest priority rule that matches right now
        for rule in sorted(rules, key=lambda r: r.priority, reverse=True):
            if not rule.predicate(metrics):
                continue

            return rule.mood

        return IDLE_COMBINATION

    def getMoodCombination(self) -> tuple[str, str]:
        if self.KeyListener.lastKeyPress is None:
            return IDLE_COMBINATION
        
        idle = time.time() - self.KeyListener.lastKeyPress

        # no activity = asleep
        # factz
        if idle >= SLEEP_DELTA_THRESHOLD:
            return ASLEEP_COMBINATION

        # tired mode
        if idle >= (SLEEP_DELTA_THRESHOLD / 3):
            return TIRED_COMBINATION
    
        return self.chooseMood(idle)
