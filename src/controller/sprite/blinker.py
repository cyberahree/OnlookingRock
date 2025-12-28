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
        blinkDelayRange: tuple[int, int],
    ):
        self.timer = timer
        self.blinkDelayRange = blinkDelayRange

        self.isBlinking = False
        self.triggerBlink = triggerBlink
        self.completeBlink = completeBlink

        timer.timeout.connect(self._onBlink)
        timer.timeout.connect(self._onBlinkComplete)

        self.scheduleBlink()

    def _onBlink(self) -> None:
        self.isBlinking = True
        self.triggerBlink()
    
    def _onBlinkComplete(self) -> None:
        self.isBlinking = False
        self.completeBlink()

    def getNextBlink(self) -> int:
        return random.randint(
            self.blinkDelayRange[0],
            self.blinkDelayRange[1]
        )

    def scheduleBlink(self):
        self.timer.stop()
        self.timer.start(self.getNextBlink())

        QTimer.singleShot(
            random.randint(100, 250),
            self.completeBlink
        )
