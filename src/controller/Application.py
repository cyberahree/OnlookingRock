from .Sprite import SpriteSystem, ASLEEP_COMBINATION, DRAG_COMBINATION
from .Blinker import Blinker

from PySide6.QtWidgets import QApplication, QLabel, QWidget
from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import Qt, QTimer

import sys

APPLICATION = QApplication(sys.argv)

UPDATE_FREQUENCY = (1/60) * 1000 # milliseconds
BLINK_RANGE = (4000, 12000) # milliseconds

class RockinWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.Sprite = SpriteSystem()
        self.Blink = Blinker(
            QTimer(self),
            self.triggerBlink,
            self.completeBlink,
            BLINK_RANGE
        )

        # internal states
        self.windowDragging = False
        self.spriteBlinking = False
        self.spriteReady = False

        self.currentFace = None
        self.currentEyes = None

        self.dragDelta = None

        # window setup
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )

        self.bodyLabel = QLabel(self)
        self.faceLabel = QLabel(self)
        self.eyesLabel = QLabel(self)
        
        self.bodyLabel.setPixmap(self.Sprite.BodyMap)
        self.resize(
            self.Sprite.BodyMap.size()
        )
        
        # prepare label z-order
        self.bodyLabel.lower()
        self.faceLabel.raise_()
        self.eyesLabel.raise_()

        # initial sprite state
        self.updateSpriteFeatures(
            *ASLEEP_COMBINATION,
            True
        )

        # expression loop
        self.expressionTimer = QTimer(self)
        self.expressionTimer.timeout.connect(
            self.updateSpriteLoop
        )

        self.expressionTimer.start(
            int(UPDATE_FREQUENCY)
        )

        # show window
        self.spriteReady = True
        self.show()

    def startWindowLoop(self):
        sys.exit(
            APPLICATION.exec()
        )

    # dragging handlers
    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        
        self.dragDelta = event.globalPosition().toPoint() - self.pos()
        self.windowDragging = True

        self.updateSpriteFeatures(
            *DRAG_COMBINATION,
            True
        )
    
    def mouseMoveEvent(self, event):
        if (event.buttons() != Qt.LeftButton) or (self.dragDelta is None):
            return
        
        globalPos = event.globalPosition().toPoint()
        targetPos = globalPos - self.dragDelta

        # get targetted screen
        screen = QGuiApplication.screenAt(globalPos)

        if screen is None:
            screen = QGuiApplication.primaryScreen()
        
        # calculate application position
        # restricted to screen bounds
        screenBounds = screen.availableGeometry()

        finalX = max(
            screenBounds.left(),
            min(
                targetPos.x(),
                screenBounds.right() - self.width()
            )
        )

        finalY = max(
            screenBounds.top(),
            min(
                targetPos.y(),
                screenBounds.bottom() - self.height()
            )
        )

        self.move(finalX, finalY)

    def mouseReleaseEvent(self, _event):
        self.windowDragging = False
        self.dragDelta = None
        self.updateSpriteLoop()

    # sprite expression loop
    def updateSpriteLoop(self):
        if (not self.spriteReady) or (self.spriteBlinking):
            return
        
        self.updateSpriteFeatures(
            *self.Sprite.getMoodCombination()
            if not self.windowDragging
            else DRAG_COMBINATION
        )

    # sprite label methods
    def updateSpriteFeatures(
        self,
        faceName: str, eyesName: str,
        ignoreChecks: bool = False
    ):
        if (not self.spriteReady) and not ignoreChecks:
            return
        
        if (self.currentFace != faceName):
            self.currentFace = faceName
            self.faceLabel.setPixmap(
                self.Sprite.getFace(faceName)
            )

        if (self.currentEyes != eyesName):
            self.currentEyes = eyesName
            self.eyesLabel.setPixmap(
                self.Sprite.getEyes(eyesName)
            )

    def updateSpriteFace(
        self,
        faceName: str,
        ignoreChecks: bool = False
    ):
        if (not self.spriteReady) and not ignoreChecks:
            return
        
        if self.currentFace == faceName:
            return

        self.currentFace = faceName
        self.faceLabel.setPixmap(
            self.Sprite.getFace(faceName)
        )
    
    def updateSpriteEyes(
        self,
        eyeName: str,
        ignoreChecks: bool = False
    ):
        if (not self.spriteReady) and not ignoreChecks:
            return
        
        if self.currentEyes == eyeName:
            return
        
        self.currentEyes = eyeName
        self.eyesLabel.setPixmap(
            self.Sprite.getEyes(eyeName)
        )

    # blinking methods
    def triggerBlink(self):
        if (not self.spriteReady) or (self.spriteBlinking or self.windowDragging):
            return
        
        self.updateSpriteEyes("blink")
        self.spriteBlinking = True

    def completeBlink(self):
        if (not self.spriteReady) or (not self.spriteBlinking):
            return
        
        self.spriteBlinking = False
        self.updateSpriteLoop()