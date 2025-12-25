from PySide6.QtWidgets import QApplication, QLabel, QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap

from collections import deque
from pynput import keyboard

import threading
import time
import random
import sys
import os

ASSETS_PATH = os.path.dirname(os.path.realpath(__file__)) + "\\assets"
APPLICATION = QApplication(sys.argv)

BLINK_RANGE = (4000, 12000) # ms
IDLE_TIMEOUT = 6 # s

class KeyListenerThread():
    def __init__(self):
        self.keyDeltas = deque(maxlen=30)
        self.lastKeyTime = None

        threading.Thread(
            target = self.startListener,
            daemon = True
        ).start()

    def startListener(self):
        def onKeyPress(key):
            now = time.time()

            if getattr(self, "lastKeyTime", None) is not None:
                self.keyDeltas.append(now - self.lastKeyTime)
            
            self.lastKeyTime = now

        with keyboard.Listener(on_press=onKeyPress) as listener:
            listener.join()
    
    def averageDelta(self):
        if len(self.keyDeltas) < 5:
            return None
        
        return sum(self.keyDeltas) / len(self.keyDeltas)

class RockAssets():
    # init
    def __init__(self):
        self.eyes = {}
        self.faces = {}

        self.preloadAssets()
    
    # class methods
    def preloadAssets(self):
        self.face = QPixmap(ASSETS_PATH + "\\root.png")

        eyes_dir = os.path.join(ASSETS_PATH, "eyes")
        faces_dir = os.path.join(ASSETS_PATH, "faces")

        for eye_image_file in os.listdir(eyes_dir):
            eye_image_path = os.path.join(eyes_dir, eye_image_file)
            self.eyes[eye_image_file] = QPixmap(eye_image_path)

        for face_image_file in os.listdir(faces_dir):
            face_image_path = os.path.join(faces_dir, face_image_file)
            self.faces[face_image_file] = QPixmap(face_image_path)

class RockinWindow(QWidget):
    # init
    def __init__(self):
        super().__init__()
        
        # setup rocky variables
        self.isDragging = False
        self.isBlinking = False
        self.dragPosition = None

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        
        self.assets = RockAssets()

        # setup labels
        self.base = QLabel(self)
        self.eyes = QLabel(self)
        self.face = QLabel(self)

        self.base.setPixmap(self.assets.face)
        self.setEyes("idle.png")
        self.setFace("idle.png")

        self.base.lower()
        self.eyes.raise_()
        self.face.raise_()

        # prep window
        self.resize(self.assets.face.size())
        self.show()

        # blinking
        self.blinkTimer = QTimer(self)
        self.blinkTimer.timeout.connect(self.blink)
        self.scheduleNextBlink()

        # reaction task
        self.keyListener = KeyListenerThread()

        self.reactionTimer = QTimer(self)
        self.reactionTimer.timeout.connect(
            lambda: self.updateReaction()
        )
        self.reactionTimer.start(250)
    
    # user dragging
    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        
        self.dragPosition = event.globalPosition().toPoint()
        self.isDragging = True
        
        self.setEyes("dragging.png", True)
    
    def mouseMoveEvent(self, event):
        if (event.buttons() != Qt.LeftButton) or (self.dragPosition is None):
            return
        
        delta = event.globalPosition().toPoint() - self.dragPosition
        self.move(self.pos() + delta)
        self.dragPosition = event.globalPosition().toPoint()
    
    def mouseReleaseEvent(self, _event):
        self.isDragging = False
        self.dragPosition = None
        self.updateReaction()

    # class methods
    def setFace(self, Face: str, ignoreState: bool = False):
        if (self.isDragging or self.isBlinking) and not ignoreState:
            return

        self.currentFace = Face
        self.face.setPixmap(self.assets.faces[Face])
    
    def setEyes(self, Eyes: str, ignoreState: bool = False):
        if (self.isDragging or self.isBlinking) and not ignoreState:
            return

        self.currentEyes = Eyes
        self.eyes.setPixmap(self.assets.eyes[Eyes])
    
    def getMood(self):
        now = time.time()
        last = self.keyListener.lastKeyTime
        
        if last is None:
            return ("sleepy.png", "idle.png")
        
        delta = now - last

        if delta > IDLE_TIMEOUT:
            return ("sleepy.png", "idle.png")
        
        if delta > IDLE_TIMEOUT / 2:
            return ("idle.png", "idle.png")

        average = self.keyListener.averageDelta()

        if average is None:
            return ("idle.png", "idle.png")
        
        if average < 0.08:
            return ("rock.png", "idle.png")
        elif average < 0.1:
            return ("alert.png", "idle.png")
        elif average < 0.25:
            return ("idle.png", "idle.png")
        else:
            return ("sleepy.png", "idle.png")

    def updateReaction(self):
        eyes, face = self.getMood()
        
        self.setEyes(eyes)
        self.setFace(face)

    def blink(self):
        if self.isDragging or self.isBlinking:
            self.scheduleNextBlink()
            return

        self.isBlinking = True
        self.setEyes("blinking.png", True)

        def unblink():
            self.isBlinking = False
            self.updateReaction()

        QTimer.singleShot(random.randint(100, 300), unblink)
        self.scheduleNextBlink()
    
    def scheduleNextBlink(self):
        delay = random.randint(BLINK_RANGE[0], BLINK_RANGE[1])
        self.blinkTimer.start(delay)

RockinWindow = RockinWindow()

sys.exit(
    APPLICATION.exec()
)
