#!/usr/bin/env python3
from .config import ConfigController

from .system.sound import SoundManager, SoundCategory
from .system.dragger import WindowDragger
from .system.timings import TimingClock

from .interfaces.windows.startmenu import StartMenuComponent, MenuAction
from .interfaces.windows.volume import VolumeWindowComponent
from .interfaces.windows.sprite import SpriteWindowComponent
from .interfaces.base import InterfaceManager

from .sprite import SpriteSystem, limitScale, IDLE_COMBINATION, DRAG_COMBINATION
from .sprite.lasermouse import LaserMouseController
from .sprite.blinker import BlinkingController
from .sprite.hat import HatOverlayWindow

from .widgets.speech import SpeechBubbleController
from .widgets.decoration import DecorationSystem

from PySide6.QtWidgets import QApplication, QLabel, QWidget
from PySide6.QtCore import Qt, QTimer

import sys

APPLICATION = QApplication(sys.argv)

class RockinWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()

        ##############################
        # 1) config + settings store #
        ##############################
        self.config = ConfigController()

        ##############################
        # 2) internal state defaults #
        ##############################
        self.currentSpriteScale = self.config.getValue("sprite.scale")
        self.spriteReady = False
        self.currentFace = None
        self.currentEyes = None
        self.currentHat = None

        #############################################
        # 3) clocks (other systems depend on these) #
        #############################################
        self.primaryClock = TimingClock(
            self.config.getValue("sprite.refreshRates.primaryLoop"),
            self
        )
    
        self.secondaryClock = TimingClock(
            self.config.getValue("sprite.refreshRates.secondaryLoop"),
            self
        )

        ####################################################
        # 4) core managers (used by signals + controllers) #
        ####################################################
        self.soundManager = SoundManager(self)
        self.spriteSystem = SpriteSystem(self)

        ##########################################################
        # 5) window flags + labels (needed before scale updates) #
        ##########################################################
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )

        self.hatOverlay = HatOverlayWindow(self)
        self.bodyLabel = QLabel(self)
        self.faceLabel = QLabel(self)
        self.eyesLabel = QLabel(self)

        # set body pixmap and resize sprite window
        body_pixmap = self.spriteSystem.getBody(self.currentSpriteScale)
        self.bodyLabel.setPixmap(body_pixmap)
        self.resize(body_pixmap.size())
        
        # size all labels to match window
        for label in (self.bodyLabel, self.faceLabel, self.eyesLabel):
            label.resize(body_pixmap.size())

        # z-order
        self.bodyLabel.lower()
        self.eyesLabel.raise_()
        self.faceLabel.raise_()

        # sprite hat
        self.currentHat = self.spriteSystem.spriteAssets.getRandom("hats")

        self.hatOverlay.setHatPixmap(
            self.spriteSystem.getHat(
                self.currentHat,
                self.currentSpriteScale
            )
        )

        ###############################################
        # 6) controllers that depend on sprite/window #
        ###############################################
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

        ##############################
        # 7) interfaces / UI systems #
        ##############################
        self.interfaceManager = InterfaceManager(self)

        self.volumeEditor = VolumeWindowComponent(
            self,
            self.secondaryClock,
            self.config,
            self.soundManager
        )

        self.spriteEditor = SpriteWindowComponent(
            self,
            self.secondaryClock,
            self.config
        )

        self.startMenu = StartMenuComponent(
            self,
            [
                MenuAction("settings", "sprite", lambda: self.interfaceManager.open("spriteEditor"), "settings"),
                MenuAction("editVolume", "volume", lambda: self.interfaceManager.open("volumeEditor"), "sound"),
                MenuAction("quitSprite", "quit", self.triggerShutdown, "power")
            ],
            lambda: not self.interfaceManager.isAnyOpen(),
            self.secondaryClock,
            occludersProvider=lambda: [self.volumeEditor, self.spriteEditor],
        )

        self.decorations = DecorationSystem(self, self.primaryClock)

        self.speechBubble = SpeechBubbleController(
            self,
            self.secondaryClock,
            occludersProvider=lambda: [self.startMenu, self.volumeEditor, self.spriteEditor]
        )

        self.interfaceManager.registerComponent(
            "startMenu",
            self.startMenu
        )

        self.interfaceManager.registerComponent(
            "volumeEditor",
            self.volumeEditor,
            False
        )

        self.interfaceManager.registerComponent(
            "spriteEditor",
            self.spriteEditor,
            False
        )

        self.interfaceManager.registerComponent(
            "speechBubbles",
            self.speechBubble.bubble,
            True
        )

        ###################################
        # 8) settings value updates       #
        ###################################
        self.config.onValueChanged.connect(self.configUpdated)

        ###########################
        # 9) initial sprite setup #
        ###########################
        self.updateSpriteFeatures(*IDLE_COMBINATION, True)
        self.setSpriteScale(self.currentSpriteScale)

        # main loop
        self.primaryClock.timer.timeout.connect(self.updateSpriteLoop)

        # show window
        self.show()

    # events
    def configUpdated(self, path: str, value: object):
        if path.startswith("sound."):
            # volume changes
            if path == "sound.masterVolume":
                self.soundManager.setMasterVolume(float(value))
            else:
                category = path[len("sound.categoryVolumes."):]
                self.soundManager.setCategoryVolume(category, float(value))
        elif path == "sprite.scale":
            # scale changes
            self.setSpriteScale(float(value))
        elif path.startswith("sprite.refreshRates"):
            # refresh rate changes
            self.primaryClock.setRefreshRate(
                self.config.getValue("sprite.refreshRates.primaryLoop")
            )

            self.secondaryClock.setRefreshRate(
                self.config.getValue("sprite.refreshRates.secondaryLoop")
            )
        else:
            pass

    def moveEvent(self, event):
        super().moveEvent(event)

        try:
            self.hatOverlay.reposition()
            self.hatOverlay.raise_()
        except Exception:
            pass

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

        userNick = self.config.getValue("sprite.userNick")

        if (userNick is None) or (userNick == "<USERNAME>"):
            def nameInputted(name):
                self.config.setValue("sprite.userNick", name)
                self.speechBubble.addSpeech(f"nice to meet you, {name}! :3")
                self.speechBubble.addSpeech("i hope you're doing well today! :D")

            self.speechBubble.addSpeech(
                "hey there! i'm rockin :3"
            )

            self.speechBubble.askSpeech(
                "what's your name?",
                interactive=True,
                onConfirm=nameInputted,
                inputPlaceholder="my name is..."
            )
        else:
            self.speechBubble.addSpeech(f"hey there {userNick}! :3")
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
            # Resize label to match new window size
            label.resize(newRootSize)
            
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

        # resize hat overlay
        self.hatOverlay.setHatPixmap(
            self.spriteSystem.getHat(
                self.currentHat,
                self.currentSpriteScale
            )
        )
        
        # reposition widgets
        self.speechBubble.bubble._reposition()
        self.startMenu._reposition()

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

