from ..system.keyboard import KeyListener
from ..asset import AssetController

from PySide6.QtGui import QPixmap
from pathlib import Path

import time

ASLEEP_COMBINATION = ("idle", "sleepy")
BLINK_COMBINATION = ("idle", "blink")
DRAG_COMBINATION = ("idle", "dragged")
IDLE_COMBINATION = ("idle", "idle")

SLEEP_DELTA_THRESHOLD = 120

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

    def getMoodCombination(self) -> tuple[str, str]:
        # no keys have been pressed since the program started
        if self.KeyListener.lastKeyPress is None:
            return IDLE_COMBINATION
        
        # idling state
        delta = time.time() - self.KeyListener.lastKeyPress

        if delta >= SLEEP_DELTA_THRESHOLD:
            self.KeyListener.keyDeltas.clear()
            return ASLEEP_COMBINATION
        
        if delta >= SLEEP_DELTA_THRESHOLD / 2:
            return IDLE_COMBINATION
        
        # key-pressing activity state
        averageDelta = self.KeyListener.getAverageDelta()

        if averageDelta is None:
            return IDLE_COMBINATION
        
        if averageDelta < 0.08:
            return ("rock", "idle")
        elif averageDelta < 0.1:
            return ("idle", "alert")
        elif averageDelta < 0.25:
            return IDLE_COMBINATION
        else:
            return ASLEEP_COMBINATION
