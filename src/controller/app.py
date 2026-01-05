#!/usr/bin/env python3
from .location import LocationServices
from .config import ConfigController

from .system.sound import SoundManager, SoundCategory
from .system.timings import TimingClock

from .scene import SceneSystem

from .interfaces.windows.startmenu import StartMenuComponent, MenuAction
from .interfaces.windows.volume import VolumeWindowComponent
from .interfaces.windows.sprite import SpriteWindowComponent
from .interfaces.windows.scene import SceneWindowComponent
from .interfaces.windows.mediaview import MediaViewWindow
from .interfaces.base import InterfaceManager

from .sprite.petting import CircularPettingController
from .sprite.speech import SpeechBubbleController
from .sprite.eyetrack import LaserMouseController
from .sprite.blinking import BlinkingController
from .sprite.cosmetic import HatOverlayWindow
from .sprite.dragger import SpriteDragger

from .sprite.templates import (
    USER_FEELING_TEMPLATE,
    TIME_TEMPLATE,
    CUTE_FACES,
    pickRandom
)

from .sprite import (
    SpriteSystem,
    limitScale,
    IDLE_COMBINATION,
    DRAG_COMBINATION
)

from .events import EventManager, InteractabilityFlags

from PySide6.QtWidgets import QApplication, QLabel, QWidget
from PySide6.QtCore import Qt, QTimer

import sys

APPLICATION = QApplication(sys.argv)

class RockinWindow(QWidget):
    """
    the main application window for the rockin sprite.
    
    manages sprite rendering, user interactions, configuration, and all subsystems including sound, scene, and UI interfaces.
    """

    def __init__(self) -> None:
        """
        initialise the rockin window and all subsystems.
        """

        super().__init__()

        ########################
        # 1) config + services #
        ########################
        self.config = ConfigController()
        self.locationServices = LocationServices(self.config)

        ##############################
        # 2) internal state defaults #
        ##############################
        self.currentSpriteScale = self.config.getValue("sprite.scale")
        self.spriteReady = False

        self.previouslyPetting = False
        self.spritePetting = False

        self.currentFace = None
        self.currentEyes = None
        self.currentHat = None

        self.eventInteractability = InteractabilityFlags()

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

        ####################
        # 4) core managers #
        ####################
        self.soundManager = SoundManager(self)
        self.spriteSystem = SpriteSystem(self)
        self.sceneSystem = SceneSystem(self, self.primaryClock)

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
        self.allHats = [str(path.stem) for path in self.spriteSystem.spriteAssets.listDirectory("hats")]
        self.currentHat = self.config.getValue("sprite.hat")

        self.hatOverlay.setHatPixmap(
            self.spriteSystem.getHat(
                self.currentHat,
                self.currentSpriteScale
            )
        )

        ###############################################
        # 6) controllers that depend on sprite/window #
        ###############################################
        self.dragger = SpriteDragger(
            self,
            onDragStart=self.onDragStart,
            onDragEnd=self.onDragEnd,
            canDrag=lambda: self.spriteReady and self.eventInteractability.isEnabled("drag")
        )

        self.blinkController = BlinkingController(
            QTimer(self),
            self.triggerBlink,
            self.updateSpriteLoop,
            lambda: not self.spritePetting and self.eventInteractability.isEnabled("blink")
        )

        self.pettingController = CircularPettingController(
            self,
            canPet=lambda: (
                (not self.blinkController.isBlinking) and
                (not self.dragger.isDragging) and
                self.eventInteractability.isEnabled("petting")
            )
        )

        self.laserMouse = LaserMouseController(
            self,
            canTrack=lambda: (
                (not self.blinkController.isBlinking) and
                (not self.dragger.isDragging) and
                self.eventInteractability.isEnabled("eyetrack")
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

        self.sceneEditor = SceneWindowComponent(
            self,
            self.secondaryClock,
            self.config,
            self.sceneSystem
        )

        self.mediaView = MediaViewWindow(
            self,
            self.secondaryClock
        )

        self.startMenu = StartMenuComponent(
            self,
            [
                MenuAction("triggerEvent", "start event", lambda: self.eventManager.triggerRandomEvent(), "event"),
                MenuAction("scene", "scene", lambda: self.interfaceManager.open("sceneEditor"), "scene"),
                MenuAction("settings", "sprite", lambda: self.interfaceManager.open("spriteEditor"), "settings"),
                MenuAction("editVolume", "volume", lambda: self.interfaceManager.open("volumeEditor"), "sound"),
                MenuAction("quitSprite", "quit", self.triggerShutdown, "power")
            ],
            lambda: (not self.interfaceManager.isAnyOpen()) and self.eventInteractability.isEnabled("startmenu"),
            self.secondaryClock
        )

        self.speechBubble = SpeechBubbleController(
            self,
            self.secondaryClock,
            occludersProvider=lambda: [
                self.startMenu,
                self.volumeEditor,
                self.spriteEditor,
                self.sceneEditor,
                self.mediaView
            ]
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
            "sceneEditor",
            self.sceneEditor,
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

        self.interfaceManager.registerComponent(
            "mediaView",
            self.mediaView,
            False
        )

        #####################
        # 8) events manager #
        #####################
        self.eventManager = EventManager(
            sprite=self,
            config=self.config,
            flags=self.eventInteractability,
            soundManager=self.soundManager,
            sceneSystem=self.sceneSystem,
            speechBubble=self.speechBubble,
            mediaView=self.mediaView,
            canRun=lambda: (
                self.spriteReady
                and (not self.dragger.isDragging)
                and (not self.interfaceManager.isAnyOpen("startMenu"))
            ),
        )

        ###################################
        # 8) settings value updates       #
        ###################################
        self.config.onValueChanged.connect(self._onConfigChange)

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
    def _onConfigChange(self, path: str, value: object):
        """
        handle configuration value changes and update relevant systems.
        
        :param path: the configuration path that changed
        :type path: str
        :param value: the new configuration value
        :type value: object
        """

        if not path.startswith("sprite."):
            return
        
        path = path[len("sprite."):]
        
        if path == "scale":
            # scale changes
            self.setSpriteScale(float(value))
        elif path == "hat":
            self.currentHat = str(value)
            self.hatOverlay.setHatPixmap(
                self.spriteSystem.getHat(
                    self.currentHat,
                    self.currentSpriteScale
                )
            )
        elif path.startswith("refreshRates"):
            # refresh rate changes
            self.primaryClock.setRefreshRate(
                self.config.getValue("sprite.refreshRates.primaryLoop")
            )

            self.secondaryClock.setRefreshRate(
                self.config.getValue("sprite.refreshRates.secondaryLoop")
            )

    def moveEvent(self, event):
        """
        handle window move event to reposition hat overlay.
        
        :param event: the move event
        """

        super().moveEvent(event)

        try:
            self.hatOverlay.reposition()
            self.hatOverlay.raise_()
        except Exception:
            pass

    def keyPressEvent(self, event):
        """
        handle key press events for menu toggle and shutdown.
        
        :param event: the key press event
        """

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
        """
        handle mouse press for dragging and menu interaction.
        
        :param event: the mouse press event
        """

        button = event.button()

        if (button == Qt.LeftButton) and self.dragger.canDrag():
                self.soundManager.playAmbientAudio("dragging")
                self.dragger.handleMousePress(event)
                event.accept()
        elif button == Qt.RightButton:
            self.interfaceManager.toggle("startMenu")
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """
        handle mouse move to update speech bubble and dragging.
        
        :param event: the mouse move event
        """

        self.speechBubble.bubble._reposition()
        self.dragger.handleMouseMove(event)

    def mouseReleaseEvent(self, event):
        """
        handle mouse release to end dragging and stop ambient audio.
        
        :param event: the mouse release event
        """

        self.soundManager.stopAmbientAudio()
        self.dragger.handleMouseRelease(event)
    
    def onDragStart(self):
        """
        handle drag start by switching to drag sprite features.
        """

        self.updateSpriteFeatures(
            *DRAG_COMBINATION
        )
    
    def onDragEnd(self):
        """
        handle drag end by updating sprite to default features.
        """

        self.updateSpriteLoop()

    def _onStartupComplete(self):
        self.spriteReady = True
        self.eventManager.start()

    # app methods
    def startWindowLoop(self):
        """
        start the main application window loop with greeting sequence.
        """

        # persistent position
        lastX = self.config.getValue("sprite.lastPosition.x")
        lastY = self.config.getValue("sprite.lastPosition.y")
        lastScreenIndex = self.config.getValue("sprite.lastPosition.screen")

        if lastScreenIndex >= len(APPLICATION.screens()):
            lastScreenIndex = len(APPLICATION.screens()) - 1
        
        screenGeometry = APPLICATION.screens()[lastScreenIndex].geometry()
        isOutsideOfScreen = not screenGeometry.contains(int(lastX), int(lastY))

        if (lastX is None or lastY is None) or isOutsideOfScreen:
            lastX = screenGeometry.x() + (screenGeometry.width() - self.width()) / 2
            lastY = screenGeometry.y() + (screenGeometry.height() - self.height()) / 2

        self.move(int(lastX), int(lastY))

        # startup sound
        self.soundManager.playSound(
            "applicationStart.wav",
            SoundCategory.SPECIAL,
            onFinish=self._onStartupComplete
        )

        # greeting sequence
        userNick = self.config.getValue("sprite.userNick")

        timeDescription = pickRandom(TIME_TEMPLATE).format(
            self.locationServices.getFriendlyLocalTime()
        )

        # collect user nickname if not set
        if (userNick is None) or (userNick == "<USERNAME>"):
            self.collectUserNickname()
        else:
            self.speechBubble.addSpeech(f"hey there {userNick}! :3")

        self.speechBubble.addSpeech(timeDescription)
        self.speechBubble.addSpeech(pickRandom(USER_FEELING_TEMPLATE).format(userNick))

        sys.exit(APPLICATION.exec_())

    def triggerShutdown(self):
        """
        trigger application shutdown with shutdown animation and sound.
        """

        if not self.spriteReady:
            return

        self.eventManager.stop()

        self.spriteReady = False
        self.updateSpriteFeatures("empty", "shuttingdown", True)

        self.config.setValue(
            "sprite.lastPosition.x",
            self.x()
        )

        self.config.setValue(
            "sprite.lastPosition.y",
            self.y()
        )

        self.config.setValue(
            "sprite.lastPosition.screen",
            APPLICATION.screens().index(self.screen())
        )

        self.speechBubble.shutdown()
        self.soundManager.playSound(
            "applicationEnd.wav",
            SoundCategory.SPECIAL,
            onFinish=self.shutdown,
            finishDelay=500
        )

    def shutdown(self):
        """
        shutdown the application and clean up resources.
        """

        self.soundManager.shutdown()

        self.config.saveConfig()
        APPLICATION.quit()

    # introduction
    def collectUserNickname(self):
        def nameInputted(name):
            self.config.setValue("sprite.userNick", name)
            self.speechBubble.addSpeech(f"nice to meet you, {name}! :3")

        self.speechBubble.addSpeech(
            "hey there! i'm rockin :3"
        )

        self.speechBubble.askSpeech(
            "what's your name?",
            interactive=True,
            onConfirm=nameInputted,
            inputPlaceholder="my name is..."
        )

    # sprite methods
    def setSpriteScale(self, scale: float):
        """
        set the sprite scale and update all related graphics.
        
        :param scale: the new sprite scale factor
        :type scale: float
        """

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
        """
        update sprite animation state on each clock tick.
        """

        if not self.spriteReady:
            return
        
        # when autopilot is disabled, events are expected to drive face/eyes directly.
        if not self.eventInteractability.isEnabled("autopilot"):
            self.spritePetting = False
            self.previouslyPetting = False
            return
        
        # 1) if the sprite is being pet, set the features of
        #    sprite to petting state
        self.spritePetting = self.pettingController.update()

        if self.spritePetting:
            if (not self.previouslyPetting) and len(self.speechBubble.queue) < 1 and (not self.speechBubble.active):
                self.speechBubble.addSpeech(
                    pickRandom(CUTE_FACES)
                )

            self.previouslyPetting = True
            self.updateSpriteFeatures(
                "idle", "petting", True
            )

            return
        else:
            self.previouslyPetting = False
        
        # 2) otherwise, update sprite features based on keyboard
        #    state or a dragging state
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
        """
        update the sprite's face and eyes to given names.
        
        :param faceName: the name of the face to display
        :type faceName: str
        :param eyesName: the name of the eyes to display
        :type eyesName: str
        :param forceful: whether to update even if blinking
        :type forceful: bool
        """

        if (not self.spriteReady or self.blinkController.isBlinking) and not forceful:
            return
        
        if (self.currentFace != faceName) and (faceName is not None):
            self.currentFace = faceName
            self.faceLabel.setPixmap(
                self.spriteSystem.getFace(faceName, self.currentSpriteScale)
            )

        if (self.currentEyes != eyesName) and (eyesName is not None):
            self.currentEyes = eyesName
            self.eyesLabel.setPixmap(
                self.spriteSystem.getEyes(eyesName, self.currentSpriteScale)
            )

    def updateSpriteFace(
        self,
        faceName: str
    ):
        """
        update the sprite's face only.
        
        :param faceName: the name of the face to display
        :type faceName: str
        """

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
        """
        update the sprite's eyes only.
        
        :param eyeName: the name of the eyes to display
        :type eyeName: str
        """

        if not self.spriteReady or self.blinkController.isBlinking:
            return
        
        self.currentEyes = eyeName
        self.eyesLabel.setPixmap(
            self.spriteSystem.getEyes(eyeName, self.currentSpriteScale)
        )

    def triggerBlink(self):
        """
        trigger a blink animation.
        """

        if (not self.spriteReady):
            return
        
        self.updateSpriteEyes("blink")
