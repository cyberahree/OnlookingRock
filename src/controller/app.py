#!/usr/bin/env python3
from .config import ConfigController

from .system.sound import SoundManager, SoundCategory
from .system.dragger import WindowDragger

from .interfaces.components.startmenu import StartMenuComponent, MenuAction
# TODO: uncomment when i actually am happy with the settings
# from .interfaces.components.settingsmodal import SettingsModalComponent
from .interfaces.base import InterfaceManager

from .sprite import SpriteSystem, limitScale, IDLE_COMBINATION, DRAG_COMBINATION
from .sprite.lasermouse import LaserMouseController
from .sprite.blinker import BlinkingController

from .widgets.notifications import NotificationController
from .widgets.speech import SpeechBubbleController
from .widgets.decoration import DecorationSystem

from PySide6.QtWidgets import QApplication, QLabel, QWidget
from PySide6.QtCore import Qt, QTimer

import sys

APPLICATION = QApplication(sys.argv)

APP_REFRESH_RATE = 60 # frames per second
SECONDARY_REFRESH_RATE = 30 # frames per second

class RockinWindow(QWidget):
    def __init__(
        self,
        configProfile: str = "default"
    ) -> None:
        super().__init__()

        self.config = ConfigController(
            profile=configProfile
        )

        # sound controller
        self.soundManager = SoundManager(self)

        # sprite controller systems
        self.currentSpriteScale = self.config.getValue("sprite.scale")
        self.spriteSystem = SpriteSystem(self, self.currentSpriteScale)
        
        self.dragger = WindowDragger(
            self,
            onDragStart=self.onDragStart,
            onDragEnd=self.onDragEnd
        )

        self.blinkController = BlinkingController(
            QTimer(self),
            self.triggerBlink,
            self.updateSpriteLoop
        )

        self.laserMouse = LaserMouseController(
            self,
            canTrack=lambda: (
                (not self.blinkController.isBlinking) and
                (not self.dragger.isDragging)
            )
        )

        # interfaces
        self.interfaceManager = InterfaceManager(self)
        self.notificationController = NotificationController(
            self,
            SECONDARY_REFRESH_RATE
        )

        # settings modal
        """
        # TODO: uncomment when i actually am happy with the settings
        self.settingsModal = SettingsModalComponent(
            self,
            SECONDARY_REFRESH_RATE,
        )

        self.interfaceManager.registerComponent(
            "settings",
            self.settingsModal
        )
        """

        # start menu
        self.startMenu = StartMenuComponent(
            self,
            [
                MenuAction("openSettings", "Settings", lambda: print("open settings"), "settings"),
                MenuAction("quitSprite", "Quit", self.triggerShutdown, "power")
            ],
            SECONDARY_REFRESH_RATE,
            #occludersProvider=lambda: [self.settingsModal]
        )

        self.interfaceManager.registerComponent(
            "startMenu",
            self.startMenu
        )

        # widgets
        self.decorations = DecorationSystem(self, APP_REFRESH_RATE)

        self.speechBubble = SpeechBubbleController(
            self,
            SECONDARY_REFRESH_RATE,
            occludersProvider=lambda: [self.startMenu]
            #occludersProvider=lambda: [self.startMenu, self.settingsModal]
        )

        self.interfaceManager.registerComponent(
            "speechBubbles",
            self.speechBubble.bubble
        )

        # internal states
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
        
        self.bodyLabel.setPixmap(self.spriteSystem.getBody(self.currentSpriteScale))
        self.resize(
            self.spriteSystem.getBody(self.currentSpriteScale).size()
        )
        
        # prepare label z-order
        self.bodyLabel.lower()
        self.eyesLabel.raise_()
        self.faceLabel.raise_()

        # apply config
        self.userNickname = self.config.getValue("user.nickname")
        self.userLanguage = self.config.getValue("user.languagePreference")

        self.soundManager.setMasterVolume(
            self.config.getValue("sound.masterVolume")
        )

        for category, volume in self.config.getValue("sound.categoryVolumes").items():
            self.soundManager.setCategoryVolume(
                category,
                volume
            )

        # sprite
        self.updateSpriteFeatures(
            *IDLE_COMBINATION, True
        )

        self.setSpriteScale(self.currentSpriteScale)

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

    # events
    def keyPressEvent(self, event):
        if not self.isActiveWindow():
            return

        if not self.spriteReady:
            return

        if event.key() == Qt.Key_E:
            self.startMenu.open()
            event.accept()
            return

        if event.key() == Qt.Key_Escape:
            self.triggerShutdown()
            event.accept()
            return

        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        btn = event.button()

        if btn == Qt.LeftButton:
            self.soundManager.playAmbientAudio("dragging")
            self.dragger.handleMousePress(event)
            event.accept()
        elif btn == Qt.RightButton:
            self.interfaceManager.toggle("startMenu")
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        self.speechBubble.bubble._reposition()
        self.dragger.handleMouseMove(event)

    def mouseReleaseEvent(self, event):
        self.soundManager.stopAmbientAudio()
        self.dragger.handleMouseRelease(event)
    
    def onDragStart(self):
        self.updateSpriteFeatures(
            *DRAG_COMBINATION
        )
    
    def onDragEnd(self):
        self.updateSpriteLoop()

    # app methods
    def startWindowLoop(self):
        self.soundManager.playSound(
            "applicationStart.wav",
            SoundCategory.SPECIAL,
            onFinish=lambda: setattr(self, "spriteReady", True)
        )

        self.notificationController.info("Saved", "Your settings were saved.")

        self.speechBubble.addSpeech("gooooodd mythical mornningg :3")
        self.speechBubble.addSpeech("how are you doing today?")

        sys.exit(APPLICATION.exec_())

    def triggerShutdown(self):
        if not self.spriteReady:
            return

        self.spriteReady = False
        self.updateSpriteFeatures("empty", "shuttingdown", True)

        self.speechBubble.shutdown()

        self.soundManager.playSound(
            "applicationEnd.wav",
            SoundCategory.SPECIAL,
            onFinish=self.shutdown,
            finishDelay=500
        )

    def shutdown(self):
        self.config.saveConfig()
        self.decorations.shutdown()
        self.soundManager.shutdown()

        APPLICATION.quit()

    # sprite methods
    def setSpriteScale(self, scale: float):
        scale = limitScale(scale)

        if self.currentSpriteScale == scale:
            return

        self.currentSpriteScale = scale
        self.config.setValue("sprite.scale", scale)

        # resize window and labels
        scaledBodyPixmap = self.spriteSystem.getBody(scale)
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
                    self.spriteSystem.getFace(
                        self.currentFace,
                        scale
                    )
                )
            elif label == self.eyesLabel:
                label.setPixmap(
                    self.spriteSystem.getEyes(
                        self.currentEyes,
                        scale
                    )
                )
            else:
                pass
        
        # reposition speech bubble
        self.speechBubble.bubble._reposition()

    def updateSpriteLoop(self):
        if not self.spriteReady:
            return
        
        self.laserMouse.update()
        
        self.updateSpriteFeatures(
            *self.spriteSystem.getMoodCombination()
            if not self.dragger.isDragging
            else DRAG_COMBINATION
        )

    def updateSpriteFeatures(
        self,
        faceName: str, eyesName: str,
        forceful: bool = False
    ):
        if (not self.spriteReady or self.blinkController.isBlinking) and not forceful:
            return
        
        if (self.currentFace != faceName):
            self.currentFace = faceName
            self.faceLabel.setPixmap(
                self.spriteSystem.getFace(faceName, self.currentSpriteScale)
            )

        if (self.currentEyes != eyesName):
            self.currentEyes = eyesName
            self.eyesLabel.setPixmap(
                self.spriteSystem.getEyes(eyesName, self.currentSpriteScale)
            )

    def updateSpriteFace(
        self,
        faceName: str
    ):
        if not self.spriteReady or self.blinkController.isBlinking:
            return
        
        if self.currentFace == faceName:
            return

        self.currentFace = faceName
        self.faceLabel.setPixmap(
            self.spriteSystem.getFace(faceName, self.currentSpriteScale)
        )
    
    def updateSpriteEyes(
        self,
        eyeName: str
    ):
        if not self.spriteReady or self.blinkController.isBlinking:
            return
        
        self.currentEyes = eyeName
        self.eyesLabel.setPixmap(
            self.spriteSystem.getEyes(eyeName, self.currentSpriteScale)
        )

    def triggerBlink(self):
        if (not self.spriteReady):
            return
        
        self.updateSpriteEyes("blink")

