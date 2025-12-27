from ..system.keyboard import KeyListener
from ..asset import AssetController

from PySide6.QtGui import QPixmap

from dataclasses import dataclass
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

class SpriteSystem:
    def __init__(self, _spriteParent):
        self.SpriteAssets = AssetController("images/sprite")
        self.KeyListener = KeyListener()

        self.BodyMap = None
        self.FaceMaps = {}
        self.EyeMaps = {}

        self._loadAssets()

    def _loadAssets(self):
        # completely reload all assets
        self.BodyMap = QPixmap(
            str(self.SpriteAssets.getAsset("root.png"))
        )
        
        for eyeFile in self.SpriteAssets.iterateDirectory("eyes", ".png"):
            self.EyeMaps[eyeFile.stem] = QPixmap(
                str(eyeFile)
            )

        for faceFile in self.SpriteAssets.iterateDirectory("faces", ".png"):
            self.FaceMaps[faceFile.stem] = QPixmap(
                str(faceFile)
            )
    
    def getFace(self, faceName: str) -> QPixmap:
        return self.FaceMaps.get(
            faceName,
            QPixmap()
        )
    
    def getEyes(self, eyesName: str) -> QPixmap:
        return self.EyeMaps.get(
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
