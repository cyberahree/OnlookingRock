#!/usr/bin/env python3
from .config.settingsstore import SettingsStore
from .config import ConfigController

from .system.sound import SoundManager, SoundCategory
from .system.dragger import WindowDragger
from .system.timings import TimingClock

from .interfaces.components.startmenu import StartMenuComponent, MenuAction
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

class RockinWindow(QWidget):
    """
    
    initialisation steps:
    1. config + settings store
    2. internal state defaults
    3. clocks (other systems depend on these)
    4. core managers (used by signals + controllers)
    5. window flags + labels (needed before scale updates)
    6. controllers that depend on sprite/window
    7. interfaces / UI systems
    8. apply initial sound config
    9. initial sprite setup
    10. wire settings signals
    
    """
    def __init__(self, configProfile: str = "default") -> None:
        super().__init__()

        ##############################
        # 1) config + settings store #
        ##############################
        self.config = ConfigController(profile=configProfile)
        self.settings = SettingsStore(self.config, parent=self)

        # local cached settings (used during initial build)
        self.currentSpriteScale = self.config.getValue("sprite.scale")
        self.userNickname = self.config.getValue("user.nickname")
        self.userLanguage = self.config.getValue("user.languagePreference")

        ##############################
        # 2) internal state defaults #
        ##############################
        self.spriteReady = False
        self.currentFace = None
        self.currentEyes = None

        #############################################
        # 3) clocks (other systems depend on these) #
        #############################################
        self.primaryClock = TimingClock(
            self.settings.get("app.refreshRates.primaryLoop"),
            self
        )
        self.secondaryClock = TimingClock(
            self.settings.get("app.refreshRates.secondaryLoop"),
            self
        )

        ####################################################
        # 4) core managers (used by signals + controllers) #
        ####################################################
        self.soundManager = SoundManager(self)
        self.spriteSystem = SpriteSystem(self, self.currentSpriteScale)

        ##########################################################
        # 5) window flags + labels (needed before scale updates) #
        ##########################################################
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )

        self.bodyLabel = QLabel(self)
        self.faceLabel = QLabel(self)
        self.eyesLabel = QLabel(self)

        body_pixmap = self.spriteSystem.getBody(self.currentSpriteScale)
        self.bodyLabel.setPixmap(body_pixmap)
        self.resize(body_pixmap.size())

        # z-order
        self.bodyLabel.lower()
        self.eyesLabel.raise_()
        self.faceLabel.raise_()

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

        self.notificationController = NotificationController(
            self,
            self.secondaryClock
        )

        self.startMenu = StartMenuComponent(
            self,
            [
                MenuAction("openSettings", "Settings", lambda: print("open settings"), "settings"),
                MenuAction("quitSprite", "Quit", self.triggerShutdown, "power")
            ],
            self.secondaryClock,
        )

        self.interfaceManager.registerComponent("startMenu", self.startMenu)

        self.decorations = DecorationSystem(self, self.primaryClock)

        self.speechBubble = SpeechBubbleController(
            self,
            self.secondaryClock,
            occludersProvider=lambda: [self.startMenu]
        )
        self.interfaceManager.registerComponent(
            "speechBubbles",
            self.speechBubble.bubble
        )

        #################################
        # 8) apply initial sound config #
        #################################
        self.soundManager.setMasterVolume(
            self.config.getValue("sound.masterVolume")
        )
        for category, volume in self.config.getValue("sound.categoryVolumes").items():
            self.soundManager.setCategoryVolume(category, volume)

        ###########################
        # 9) initial sprite setup #
        ###########################
        self.updateSpriteFeatures(*IDLE_COMBINATION, True)
        self.setSpriteScale(self.currentSpriteScale)

        # main loop
        self.primaryClock.timer.timeout.connect(self.updateSpriteLoop)

        ##############################
        # 10)  wire settings signals #
        ##############################
        self._configureSettingSignals()

        # show window
        self.show()

    # settings handlers
    def _configureSettingSignals(self):
        self.settings.watch(
            "sprite.scale",
            lambda v: self.setSpriteScale(v)
        )

        self.settings.watch(
            "sprite.chattiness",
            lambda v: setattr(self, "chattiness", v)
        )

        self.settings.watch(
            "sound.masterVolume",
            lambda v: self.soundManager.setMasterVolume(v)
        )
    
        self.settings.watch(
            "sound.categoryVolumes.EVENT",
            lambda v: self.soundManager.setCategoryVolume("EVENT", v)
        )
    
        self.settings.watch(
            "sound.categoryVolumes.FEEDBACK",
            lambda v: self.soundManager.setCategoryVolume("FEEDBACK", v)
        )
    
        self.settings.watch(
            "sound.categoryVolumes.AMBIENT",
            lambda v: self.soundManager.setCategoryVolume("AMBIENT", v)
        )
    
        self.settings.watch(
            "sound.categoryVolumes.SPECIAL",
            lambda v: self.soundManager.setCategoryVolume("SPECIAL", v)
        )
    
        self.settings.watch(
            "sound.categoryVolumes.SPEECH",
            lambda v: self.soundManager.setCategoryVolume("SPEECH", v)
        )

        self.settings.watch(
            "user.nickname",
            lambda v: setattr(self, "userNickname", v)
        )
    
        self.settings.watch(
            "user.languagePreference",
            lambda v: setattr(self, "userLanguage", v)
        )

        self.settings.watch(
            "app.refreshRates.primaryLoop",
            lambda refreshRate: self.primaryClock.setRefreshRate(refreshRate)
        )

        self.settings.watch(
            "app.refreshRates.secondaryLoop",
            lambda refreshRate: self.secondaryClock.setRefreshRate(refreshRate)
        )

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

