from collections import deque
from pynput import keyboard

import threading
import time

KEY_HISTORY_MAX = 45

class KeyListener:
    """
    monitors keyboard activity and typing speed using background listener thread
    """

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
        """
        Initialise the keyboard activity listener.
        
        :param recentInputWindow: Time window in seconds for calculating keys per second
        :type recentInputWindow: int
        :param maxSpeedDelta: Maximum inter-key delta to include in typing speed average
        :type maxSpeedDelta: float
        :param minSamples: Minimum number of samples before returning average delta
        :type minSamples: int
        :param activityHalfLife: Half-life in seconds for activity decay
        :type activityHalfLife: float
        :param activityBumpPerKey: Activity energy added per keypress
        :type activityBumpPerKey: float
        """

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
        """
        decay activity level exponentially based on elapsed time.
        
        :param nowMono: Current time from monotonic clock
        :type nowMono: float
        """

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
        """
        start the background keyboard listener thread.
        """

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

    def contributeActivity(self, amount: float):
        """
        externally contribute to activity level.
        
        :param amount: Amount to add to activity level
        :type amount: float
        """

        nowMono = time.monotonic()

        with self.listenerLock:
            self._decayActivityLocked(nowMono)
            self.activity = min(1.0, self.activity + amount)

    def shutdown(self):
        """
        shutdown the keyboard listener thread.
        """

        with self.listenerLock:
            if self.listenerThread is None:
                return
            
            self.listenerThread.stop()
            self.listenerThread = None
    
    def getTimeSinceLastKeyPress(self) -> float | None:
        """
        get time in seconds since the last keyboard key was pressed.
        
        :return: Time in seconds since last keypress, or None if no keypresses recorded
        :rtype: float | None
        """

        with self.listenerLock:
            if self.lastKeyPress is None:
                return None
            
            return time.time() - self.lastKeyPress
    
    def getAverageDelta(self) -> float | None:
        """
        get the average time delta between recent keypresses.
        
        :return: Average time between keypresses in seconds, or None if insufficient samples
        :rtype: float | None
        """

        with self.listenerLock:
            if len(self.keyDeltas) < self.minSamples:
                return None
            
            return sum(self.keyDeltas) / len(self.keyDeltas)
    
    def keysPerSecond(self) -> float:
        """
        get the current typing speed in keys per second within the recent input window.
        
        :return: Keys per second
        :rtype: float
        """

        nowMono = time.monotonic()
        cutoff = nowMono - self.recentInputWindow

        with self.listenerLock:
            # cheap rolling window
            while (self.keyPressTimes and self.keyPressTimes[0] < cutoff):
                self.keyPressTimes.popleft()
            
            count = len(self.keyPressTimes)
        
        return count / self.recentInputWindow if self.recentInputWindow > 0 else 0.0
    
    def getActivityLevel(self) -> float:
        """
        get the current activity level with exponential decay applied.
        
        :return: Activity level between 0.0 and 1.0
        :rtype: float
        """

        nowMono = time.monotonic()

        with self.listenerLock:
            self._decayActivityLocked(nowMono)
            return self.activity
