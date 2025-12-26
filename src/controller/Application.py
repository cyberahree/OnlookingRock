from .sprite import SpriteSystem, ASLEEP_COMBINATION, DRAG_COMBINATION
from .system.sound import SoundManager, SoundCategory
from .system.dragger import WindowDragger
from .sprite.blinker import Blinker

from PySide6.QtWidgets import QApplication, QLabel, QWidget
from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import Qt, QTimer

import sys

APPLICATION = QApplication(sys.argv)

BLINK_RANGE = (4000, 12000) # milliseconds
REFRESH_RATE = 30 # frames per second

class RockinWindow(QWidget):
    def __init__(self):
        super().__init__()

        # sound controller
        self.Sound = SoundManager(self)

        # sprite controller systems
        self.Sprite = SpriteSystem()

        self.Blink = Blinker(
            QTimer(self),
            self.triggerBlink,
            self.completeBlink,
            BLINK_RANGE
        )

        self.Dragger = WindowDragger(
            self,
            onDragStart=self.onDragStart,
            onDragEnd=self.onDragEnd
        )

        # internal states
        self.spriteBlinking = False
        self.spriteExiting = False
        self.spriteReady = False

        self.currentFace = None
        self.currentEyes = None

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
        self.eyesLabel.raise_()
        self.faceLabel.raise_()

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
            int((1/REFRESH_RATE) * 1000)
        )

        # show window
        self.spriteReady = True
        self.show()

    def shutdown(self):
        self.Sound.shutdown()
        APPLICATION.quit()

    def startWindowLoop(self):
        self.Sound.playSound(
            "applicationStart.wav",
            SoundCategory.SPECIAL
        )

        sys.exit(APPLICATION.exec_())

    # dragging handlers
    def mousePressEvent(self, event):
        self.Dragger.handleMousePress(event)
    
    def mouseMoveEvent(self, event):
        self.Dragger.handleMouseMove(event)

    def mouseReleaseEvent(self, event):
        self.Dragger.handleMouseRelease(event)
    
    # keyboard handlers
    def keyPressEvent(self, event):
        if (event.key() != Qt.Key_Escape) or (not self.isActiveWindow()):
            return
        
        if self.spriteExiting:
            return

        self.updateSpriteFeatures("empty", "shuttingdown", True)
        self.spriteExiting = True

        self.Sound.playSound(
            "applicationEnd.wav",
            SoundCategory.SPECIAL,
            onFinish=self.shutdown,
            finishDelay=1000
        )
    
    def onDragStart(self):
        self.updateSpriteFeatures(
            *DRAG_COMBINATION,
            True
        )
    
    def onDragEnd(self):
        self.updateSpriteLoop()

    # sprite expression loop
    def updateSpriteLoop(self):
        if (not self.spriteReady) or (self.spriteBlinking):
            return
        
        self.updateSpriteFeatures(
            *self.Sprite.getMoodCombination()
            if not self.Dragger.isDragging
            else DRAG_COMBINATION
        )

    # sprite label methods
    def updateSpriteFeatures(
        self,
        faceName: str, eyesName: str,
        ignoreChecks: bool = False
    ):
        if self.spriteExiting:
            return

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
        if self.spriteExiting:
            return

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
        if self.spriteExiting:
            return

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
        if (not self.spriteReady) or (self.spriteBlinking or self.Dragger.isDragging) or self.spriteExiting:
            return
        
        self.updateSpriteEyes("blink")
        self.spriteBlinking = True

    def completeBlink(self):
        if (not self.spriteReady) or (not self.spriteBlinking) or self.spriteExiting:
            return
        
        self.spriteBlinking = False
        self.updateSpriteLoop()
