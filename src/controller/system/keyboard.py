from collections import deque
from pynput import keyboard

import threading
import time

class KeyListener:
    def __init__(self):
        self.keyDeltas = deque(maxlen=30)
        self.lastKeyPress = None

        # Initialise the thread
        threading.Thread(
            target=self.startListener,
            daemon=True
        ).start()
    
    def startListener(self):
        def onKeyPress(key):
            now = time.time()
            lastKeyPress = self.lastKeyPress

            if lastKeyPress is not None:
                self.keyDeltas.append(now - lastKeyPress)

            self.lastKeyPress = time.time()

        with keyboard.Listener(on_press=onKeyPress) as PynputListener:
            PynputListener.join()
        
    def getAverageDelta(self) -> int | None:
        if len(self.keyDeltas) < 5:
            return None
        
        return sum(self.keyDeltas) / len(self.keyDeltas)
    