from PySide6.QtCore import QObject, QTimer, QElapsedTimer, Signal, Qt

from typing import Optional

def _msFromRefreshRate(RefreshRate: int) -> int:
    return max(
        1,
        round(1000 // RefreshRate)
    )

class TimingClock(QObject):
    """
    a timing clock that emits signals at a specified refresh rate
    """

    tick = Signal(float)
    refreshRateChanged = Signal(int)

    def __init__(self, refreshRate: int = 1, parent: Optional[QObject] = None):
        """
        Initialise the timing clock.
        
        :param refreshRate: The refresh rate in hertz
        :type refreshRate: int
        :param parent: Parent QObject
        """

        super().__init__(parent)

        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.PreciseTimer)

        self.elapsedTimer = QElapsedTimer()
        self.elapsedTimer.start()
        self.refreshRate = 0
        self.lastDelta = 0

        self.timer.timeout.connect(self._onTimeout)
        self.setRefreshRate(refreshRate)
        self.timer.start()
    
    def _onTimeout(self):
        """
        handle timer timeout and emit tick signal with elapsed time.
        """

        elapsedMs = self.elapsedTimer.restart()
        self.lastDelta = elapsedMs
        self.tick.emit(elapsedMs / 1000)
    
    def setRefreshRate(self, refreshRate: int):
        """
        Set the refresh rate for the timing clock.
        
        :param refreshRate: The new refresh rate in hertz
        :type refreshRate: int
        """

        newRefreshRate = max(1, int(refreshRate))

        if newRefreshRate == self.refreshRate:
            return

        self.refreshRate = newRefreshRate
        self.intervalMs = _msFromRefreshRate(self.refreshRate)
        self.timer.setInterval(self.intervalMs)
        self.refreshRateChanged.emit(self.intervalMs)
