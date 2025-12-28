#!/usr/bin/env python3
from .config import ConfigController

from .system.sound import SoundManager, SoundCategory
from .system.dragger import WindowDragger

from .interfaces.components.startmenu import StartMenuComponent, MenuAction
from .interfaces.base import InterfaceManager

from .sprite import SpriteSystem, IDLE_COMBINATION, DRAG_COMBINATION
from .sprite.lasermouse import LaserMouseController
from .sprite.blinker import BlinkingController

from .widgets.speech import SpeechBubbleController
from .widgets.decoration import DecorationSystem

from PySide6.QtWidgets import QApplication, QLabel, QWidget
from PySide6.QtCore import Qt, QTimer

import sys

APPLICATION = QApplication(sys.argv)

BLINK_RANGE = (4000, 12000) # milliseconds

MAX_SCALE = 2.0

APP_REFRESH_RATE = 30 # frames per second
SECONDARY_REFRESH_RATE = 15 # frames per second

class RockinWindow(QWidget):
    def __init__(
        self,
        configProfile: str = None
    ) -> None:
        super().__init__()

        self.config = ConfigController(
            profile=configProfile
        )

        # sound controller
        self.Sound = SoundManager(self)

        # sprite controller systems
        self.currentSpriteScale = self.config.getValue("sprite.scale")
        self.Sprite = SpriteSystem(self, self.currentSpriteScale)
        
        self.Dragger = WindowDragger(
            self,
            onDragStart=self.onDragStart,
            onDragEnd=self.onDragEnd
        )

        self.Blink = BlinkingController(
            QTimer(self),
            self.triggerBlink,
            self.completeBlink,
            BLINK_RANGE
        )

        self.LaserMouse = LaserMouseController(
            self,
            canTrack=lambda: (
                (not self.spriteBlinking) and
                (not self.Dragger.isDragging)
            )
        )

        # interfaces
        self.InterfaceManager = InterfaceManager(self)

        # start menu
        actions = [
            MenuAction("quitSprite", "Quit", self.triggerShutdown)
        ]

        self.StartMenu = StartMenuComponent(
            self,
            actions,
            SECONDARY_REFRESH_RATE
        )

        self.InterfaceManager.registerComponent(
            "startMenu",
            self.StartMenu
        )

        # widgets
        self.Decorations = DecorationSystem(self, SECONDARY_REFRESH_RATE)

        self.SpeechBubble = SpeechBubbleController(
            self,
            SECONDARY_REFRESH_RATE,
            occludersProvider=lambda: [self.StartMenu]
        )

        # internal states
        self.spriteBlinking = False
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
        
        self.bodyLabel.setPixmap(self.Sprite.getBody(self.currentSpriteScale))
        self.resize(
            self.Sprite.getBody(self.currentSpriteScale).size()
        )
        
        # prepare label z-order
        self.bodyLabel.lower()
        self.eyesLabel.raise_()
        self.faceLabel.raise_()

        # apply config
        self.userNickname = self.config.getValue("user.nickname")
        self.userLangauge = self.config.getValue("user.languagePreference")

        self.setSpriteScale(self.currentSpriteScale)

        self.Sound.setMasterVolume(
            self.config.getValue("sound.masterVolume")
        )

        for category, volume in self.config.getValue("sound.categoryVolumes").items():
            self.Sound.setCategoryVolume(
                category,
                volume
            )

        # initial sprite state
        self.updateSpriteFeatures(
            *IDLE_COMBINATION, True
        )

        # expression loop
        self.expressionTimer = QTimer(self)
        self.expressionTimer.timeout.connect(
            self.updateSpriteLoop
        )

        self.expressionTimer.start(
            1000 // APP_REFRESH_RATE
        )

        # show window
        self.show()

    def setSpriteScale(self, scale: float):
        scale = max(0.1, min(scale, MAX_SCALE))

        if self.currentSpriteScale == scale:
            return

        self.currentSpriteScale = scale
        self.config.setValue("sprite.scale", scale)

        # resize window and labels
        scaledBodyPixmap = self.Sprite.getBody(scale)
        newRootSize = scaledBodyPixmap.size()

        self.resize(newRootSize)

        for label in (
            self.bodyLabel,
            self.faceLabel,
            self.eyesLabel
        ):
            # get scaled pixmap
            if label == self.bodyLabel:
                label.setPixmap(scaledBodyPixmap)
            elif label == self.faceLabel:
                label.setPixmap(
                    self.Sprite.getFace(
                        self.currentFace,
                        scale
                    )
                )
            elif label == self.eyesLabel:
                label.setPixmap(
                    self.Sprite.getEyes(
                        self.currentEyes,
                        scale
                    )
                )
            else:
                pass
        
        # reposition speech bubble
        self.SpeechBubble.bubble._reposition()

    def triggerShutdown(self):
        self.spriteReady = False
        self.updateSpriteFeatures("empty", "shuttingdown", True)

        self.SpeechBubble.shutdown()

        self.Sound.playSound(
            "applicationEnd.wav",
            SoundCategory.SPECIAL,
            onFinish=self.shutdown,
            finishDelay=500
        )

    # keyboard handlers
    def keyPressEvent(self, event):
        if not self.isActiveWindow():
            return

        if not self.spriteReady:
            return

        if event.key() == Qt.Key_E:
            self.StartMenu.open()
            event.accept()
            return

        if event.key() == Qt.Key_Escape:
            self.triggerShutdown()
            event.accept()
            return

        super().keyPressEvent(event)


    def shutdown(self):
        self.Decorations.shutdown()
        self.Sound.shutdown()

        APPLICATION.quit()

    def startWindowLoop(self):
        self.Sound.playSound(
            "applicationStart.wav",
            SoundCategory.SPECIAL,
            onFinish=lambda: setattr(self, "spriteReady", True)
        )

        self.SpeechBubble.addSpeech("gooooodd mythical mornningg :3")
        self.SpeechBubble.addSpeech("how are you doing today?")

        sys.exit(APPLICATION.exec_())

    # dragging handlers
    def mousePressEvent(self, event):
        btn = event.button()

        if btn == Qt.LeftButton:
            self.Sound.playAmbientAudio("dragging")
            self.Dragger.handleMousePress(event)
            event.accept()
        elif btn == Qt.RightButton:
            self.InterfaceManager.toggle("startMenu")
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        self.SpeechBubble.bubble._reposition()
        self.Dragger.handleMouseMove(event)

    def mouseReleaseEvent(self, event):
        self.Sound.stopAmbientAudio()
        self.Dragger.handleMouseRelease(event)
    
    def onDragStart(self):
        self.updateSpriteFeatures(
            *DRAG_COMBINATION
        )
    
    def onDragEnd(self):
        self.updateSpriteLoop()

    # sprite expression loop
    def updateSpriteLoop(self):
        if not self.spriteReady:
            return
        
        self.LaserMouse.update()
        
        self.updateSpriteFeatures(
            *self.Sprite.getMoodCombination()
            if not self.Dragger.isDragging
            else DRAG_COMBINATION
        )

    # sprite label methods
    def updateSpriteFeatures(
        self,
        faceName: str, eyesName: str,
        forceful: bool = False
    ):
        if (not self.spriteReady or self.spriteBlinking) and not forceful:
            return
        
        if (self.currentFace != faceName):
            self.currentFace = faceName
            self.faceLabel.setPixmap(
                self.Sprite.getFace(faceName, self.currentSpriteScale)
            )

        if (self.currentEyes != eyesName):
            self.currentEyes = eyesName
            self.eyesLabel.setPixmap(
                self.Sprite.getEyes(eyesName, self.currentSpriteScale)
            )

    def updateSpriteFace(
        self,
        faceName: str
    ):
        if not self.spriteReady or self.spriteBlinking:
            return
        
        if self.currentFace == faceName:
            return

        self.currentFace = faceName
        self.faceLabel.setPixmap(
            self.Sprite.getFace(faceName, self.currentSpriteScale)
        )
    
    def updateSpriteEyes(
        self,
        eyeName: str
    ):
        if not self.spriteReady or self.spriteBlinking:
            return
        
        self.currentEyes = eyeName
        self.eyesLabel.setPixmap(
            self.Sprite.getEyes(eyeName, self.currentSpriteScale)
        )

    # blinking methods
    def triggerBlink(self):
        if (not self.spriteReady):
            return
        
        self.updateSpriteEyes("blink")
        self.spriteBlinking = True

    def completeBlink(self):
        self.spriteBlinking = False
        self.updateSpriteLoop()
