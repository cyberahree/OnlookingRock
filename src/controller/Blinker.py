from PySide6.QtCore import QTimer
from typing import Callable

import random
import time

random.seed(
    "arisblinkyrocksystemversionsupercool" + str(time.time())
)

class Blinker:
    def __init__(
        self,
        timer: QTimer,
        triggerBlink: Callable,
        completeBlink: Callable,
        blinkDelayRange: tuple[int, int],
    ):
        self.timer = timer
        self.blinkDelayRange = blinkDelayRange

        self.triggerBlink = triggerBlink
        self.completeBlink = completeBlink

        timer.timeout.connect(self.triggerBlink)
        timer.timeout.connect(self.scheduleBlink)

        self.scheduleBlink()

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
