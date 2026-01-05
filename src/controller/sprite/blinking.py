from PySide6.QtCore import QTimer
from typing import Callable

import random
import time

random.seed(
    "arisblinkyrocksystemversionsupercool" + str(time.time())
)

class BlinkingController:
    """
    manages automatic blinking animation with configurable intervals and callbacks
    """

    def __init__(
        self,
        timer: QTimer,
        triggerBlink: Callable,
        completeBlink: Callable,
        canBlink: Callable[[], bool] = lambda: True,
        blinkIntervalRange: tuple[int, int] = (4000, 12000),
    ):
        """
        initialise the blinking controller with timer and animation callbacks.
        
        :param timer: QTimer to schedule blinks
        :type timer: QTimer
        :param triggerBlink: Callback invoked when blink animation starts
        :type triggerBlink: Callable
        :param completeBlink: Callback invoked when blink animation completes
        :type completeBlink: Callable
        :param canBlink: Callable that returns True if blinking is allowed
        :type canBlink: Callable[[], bool]
        :param blinkIntervalRange: Range for random interval between blinks (min, max) in ms
        :type blinkIntervalRange: tuple[int, int]
        """

        self.timer = timer
        self.blinkIntervalRange = blinkIntervalRange

        self.isBlinking = False
        self.canBlink = canBlink
        self.triggerBlink = triggerBlink
        self.completeBlink = completeBlink

        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._onBlink)

        self.scheduleBlink()

    def _onBlink(self) -> None:
        """
        trigger the blink animation when timer fires.
        """

        if self.isBlinking:
            return

        if not self.canBlink():
            self.scheduleBlink()
            return

        self.isBlinking = True
        self.triggerBlink()

        QTimer.singleShot(
            random.randint(100, 250),
            self._onBlinkComplete
        )
    
    def _onBlinkComplete(self) -> None:
        """
        complete the blink animation and update state.
        """

        if not self.isBlinking:
            return

        self.isBlinking = False
        self.completeBlink()
        self.scheduleBlink()

    def setBlinkIntervalRange(self, blinkIntervalRange: tuple[int, int]) -> None:
        """
        set the range for random intervals between blinks.
        
        :param blinkIntervalRange: Range (min, max) in milliseconds
        :type blinkIntervalRange: tuple[int, int]
        """

        self.blinkIntervalRange = blinkIntervalRange

    def getNextBlink(self) -> int:
        """
        get a random interval for the next blink within the configured range.
        
        :return: Random interval in milliseconds
        :rtype: int
        """

        return random.randint(
            self.blinkIntervalRange[0],
            self.blinkIntervalRange[1]
        )

    def scheduleBlink(self):
        """
        schedule the next blink with a random interval and initial completion trigger.
        """

        self.timer.stop()
        self.timer.start(self.getNextBlink())
