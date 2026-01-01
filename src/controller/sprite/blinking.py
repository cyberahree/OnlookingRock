from PySide6.QtCore import QTimer
from typing import Callable

import random
import time

random.seed(
    "arisblinkyrocksystemversionsupercool" + str(time.time())
)

class BlinkingController:
    def __init__(
        self,
        timer: QTimer,
        triggerBlink: Callable,
        completeBlink: Callable,
        canBlink: Callable[[], bool] = lambda: True,
        blinkIntervalRange: tuple[int, int] = (4000, 12000),
    ):
        self.timer = timer
        self.blinkIntervalRange = blinkIntervalRange

        self.isBlinking = False
        self.canBlink = canBlink
        self.triggerBlink = triggerBlink
        self.completeBlink = completeBlink

        timer.timeout.connect(self._onBlink)
        timer.timeout.connect(self._onBlinkComplete)

        self.scheduleBlink()

    def _onBlink(self) -> None:
        if not self.canBlink():
            return

        self.isBlinking = True
        self.triggerBlink()
    
    def _onBlinkComplete(self) -> None:
        self.isBlinking = False
        self.completeBlink()

    def setBlinkIntervalRange(self, blinkIntervalRange: tuple[int, int]) -> None:
        self.blinkIntervalRange = blinkIntervalRange

    def getNextBlink(self) -> int:
        return random.randint(
            self.blinkIntervalRange[0],
            self.blinkIntervalRange[1]
        )

    def scheduleBlink(self):
        self.timer.stop()
        self.timer.start(self.getNextBlink())

        QTimer.singleShot(
            random.randint(100, 250),
            self.completeBlink
        )
