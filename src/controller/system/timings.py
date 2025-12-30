from PySide6.QtCore import QObject, QTimer, QElapsedTimer, Signal, Qt

def _msFromRefreshRate(RefreshRate: int) -> int:
    return max(
        1,
        round(1000 // RefreshRate)
    )

class TimingClock(QObject):
    tick = Signal(float)
    refreshRateChanged = Signal(int)

    def __init__(self, refreshRate: int = 1, parent = None):
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
        elapsedMs = self.elapsedTimer.restart()
        self.lastDelta = elapsedMs
        self.tick.emit(elapsedMs / 1000)
    
    def setRefreshRate(self, refreshRate: int):
        newRefreshRate = max(1, int(refreshRate))

        if newRefreshRate == self.refreshRate:
            return

        self.refreshRate = newRefreshRate
        self.intervalMs = _msFromRefreshRate(self.refreshRate)
        self.timer.setInterval(self.intervalMs)
        self.refreshRateChanged.emit(self.intervalMs)
