from PySide6.QtCore import QObject, QTimer, QElapsedTimer, Signal, Qt

def _msFromRefreshRate(RefreshRate: int) -> int:
    return max(
        1,
        round(1000 // RefreshRate)
    )

class TimingClock(QObject):
    tick = Signal(float)

    def __init__(self, refreshRate: int = 1, parent = None):
        super().__init__(parent)

        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.PreciseTimer)

        self.elapsedTimer = QElapsedTimer()
        self.elapsedTimer.start()
        self.lastDelta = 0

        self.timer.timeout.connect(self._onTimeout)
        self.setRefreshRate(refreshRate)
        self.timer.start()
    
    def _onTimeout(self):
        elapsedMs = self.elapsedTimer.restart()
        self.lastDelta = elapsedMs
        self.tick.emit(elapsedMs / 1000)
    
    def setRefreshRate(self, refreshRate: int):
        self.refreshRate = max(1, int(refreshRate))
        self.timer.setInterval(_msFromRefreshRate(self.refreshRate))
