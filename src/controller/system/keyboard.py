from collections import deque
from pynput import keyboard

import threading
import time
import math

KEY_HISTORY_MAX = 45

class KeyListener:
    def __init__(
        self,
        # inter-key gap bigger than this should be treated as a "break"
        # and should be excluded from typing-speed avg'ing
        recentInputWindow: int = 6,
        maxSpeedDelta: float = 0.6,
        minSamples: int = 5,
        # higher = stays awake for longer
        activityHalfLife: float = 8.0,
        # how much each keypress bumps activity energy
        activityBumpPerKey: float = 0.2
    ):
        # save parameters
        self.recentInputWindow = recentInputWindow
        self.maxSpeedDelta = maxSpeedDelta
        self.minSamples = minSamples

        self.activityHalfLife = activityHalfLife
        self.activityBumpPerKey = activityBumpPerKey

        # initialise data structures
        self.keyDeltas = deque(maxlen=KEY_HISTORY_MAX)
        self.keyPressTimes = deque(maxlen=KEY_HISTORY_MAX * 4)

        self.lastKeyPress = None
        self.lastKeyPressMono = None

        self.activity = 0.0
        self.activityLastUpdateMono = time.monotonic()

        # thread
        self.listenerLock = threading.Lock()
        self.listenerThread = None

        threading.Thread(
            target=self.startListener,
            daemon=True
        ).start()

    def _decayActivityLocked(self, nowMono: float) -> None:
        if self.activityHalfLife <= 0:
            self.activityLastUpdateMono = nowMono
            return

        deltaTime = nowMono - self.activityLastUpdateMono

        if deltaTime <= 0:
            return
        
        # exponential decay :D
        # rmbk-1000 be like: activity -= decayRate * activity * deltaTime

        decay = 0.5 ** (deltaTime / self.activityHalfLife)

        self.activity *= decay
        self.activityLastUpdateMono = nowMono

    def startListener(self):
        def onKeyPress(_key):
            nowWall = time.time()
            nowMono = time.monotonic()

            with self.listenerLock:
                # update deltas
                if self.lastKeyPressMono is not None:
                    delta = nowMono - self.lastKeyPressMono

                    if delta <= self.maxSpeedDelta:
                        self.keyDeltas.append(delta)
                
                self.keyPressTimes.append(nowMono)

                self.lastKeyPressMono = nowMono
                self.lastKeyPress = nowWall

                # update activity
                self._decayActivityLocked(nowMono)
                self.activity = min(1.0, self.activity + self.activityBumpPerKey)

        with keyboard.Listener(on_press=onKeyPress) as listenerThread:
            self.listenerThread = listenerThread
            listenerThread.join()
    
    def shutdown(self):
        with self.listenerLock:
            if self.listenerThread is None:
                return
            
            self.listenerThread.stop()
            self.listenerThread = None
    
    def getTimeSinceLastKeyPress(self) -> float | None:
        with self.listenerLock:
            if self.lastKeyPress is None:
                return None
            
            return time.time() - self.lastKeyPress
    
    def getAverageDelta(self) -> float | None:
        with self.listenerLock:
            if len(self.keyDeltas) < self.minSamples:
                return None
            
            return sum(self.keyDeltas) / len(self.keyDeltas)
    
    def keysPerSecond(self) -> float:
        nowMono = time.monotonic()
        cutoff = nowMono - self.recentInputWindow

        with self.listenerLock:
            # cheap rolling window
            while (self.keyPressTimes and self.keyPressTimes[0] < cutoff):
                self.keyPressTimes.popleft()
            
            count = len(self.keyPressTimes)
        
        return count / self.recentInputWindow if self.recentInputWindow > 0 else 0.0
    
    def getActivityLevel(self) -> float:
        nowMono = time.monotonic()

        with self.listenerLock:
            self._decayActivityLocked(nowMono)
            return self.activity
