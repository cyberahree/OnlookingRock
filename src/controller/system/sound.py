from ..asset import AssetController

from .speech import buildSpeechBlips

from PySide6.QtMultimedia import QSoundEffect, QMediaPlayer, QAudioOutput
from PySide6.QtCore import QObject, QUrl, QTimer, Signal, QDateTime

from typing import Callable, List, Optional, Annotated, Any
from dataclasses import dataclass
from enum import Enum

import random
import logging

logger = logging.getLogger(__name__)

# Number of speech blip sound variations to generate
SPEECH_BLIP_COUNT = 6

class SoundCategory(Enum):
    EVENT = 0
    FEEDBACK = 1
    AMBIENT = 2
    SPECIAL = 3
    SPEECH = 4

@dataclass
class ValueRange:
    minValue: float = 0.0
    maxValue: float = 1.0

@dataclass
class CategoryConfig:
    volume: float = 1.0
    muted: bool = False
    maxPolyphony: int = 3
    audioCooldown: int = 0 # in seconds, how long until one sound can be played again

VOLUME_RANGE = ValueRange()

def clamp(value: float, rangeValues: ValueRange) -> float:
    return max(rangeValues.minValue, min(rangeValues.maxValue, value))

class SoundManager(QObject):
    """
    manages sound playback with support for multiple audio categories and volume control
    """

    mutedSignal = Signal(bool)
    
    def __init__(self, parent: Optional[QObject] = None):
        """
        initialise the sound manager.
        
        :param parent: Parent QObject
        :type parent: Optional[QObject]
        """

        super().__init__(parent)

        self.soundAssets = AssetController("sounds")
        self.config = parent.config

        self.masterMuted = False
        self.masterVolume = self.config.getValue("sound.masterVolume") or 0.5

        self.soundCategories = {
            SoundCategory.EVENT: CategoryConfig(
                volume=self.config.getValue("sound.categoryVolumes.EVENT") or 0.5,
                maxPolyphony=9
            ),

            SoundCategory.FEEDBACK: CategoryConfig(
                volume=self.config.getValue("sound.categoryVolumes.FEEDBACK") or 0.5
            ),

            SoundCategory.AMBIENT: CategoryConfig(
                volume=self.config.getValue("sound.categoryVolumes.AMBIENT") or 0.3
            ),

            SoundCategory.SPECIAL: CategoryConfig(
                volume=self.config.getValue("sound.categoryVolumes.SPECIAL") or 0.5,
            ),

            SoundCategory.SPEECH: CategoryConfig(
                volume=self.config.getValue("sound.categoryVolumes.SPEECH") or 0.6,
                maxPolyphony=SPEECH_BLIP_COUNT
            )
        }

        self.soundCache = {}
        self.cooldownCache = {}

        self.config.onValueChanged.connect(self._onConfigChange)

        # audios that loop
        self.ambientAudioOutput = QAudioOutput(self)
        self.ambientMediaPlayer = QMediaPlayer(self)

        self.ambientMediaPlayer.setAudioOutput(self.ambientAudioOutput)
        self.ambientMediaPlayer.setLoops(QMediaPlayer.Infinite)

        # generate speech blips
        buildSpeechBlips(self, SoundCategory.SPEECH, SPEECH_BLIP_COUNT)

        # array of scheduled sounds
        self.scheduledSounds: List[QTimer] = []

    # internal methods
    def _onConfigChange(self, path: str, value: Any) -> None:
        """
        handle configuration changes.
        
        :param path: Configuration path that changed
        :type path: str
        :param value: New value for the configuration
        :type value: Any
        """

        if not path.startswith("sound."):
            return
        
        path = path[len("sound."):]

        if path == "masterVolume":
            self.setMasterVolume(float(value))
        else:
            category = path[len("categoryVolumes."):]
            self.setCategoryVolume(category, float(value))

    def _massLoadSoundInstanceToCategory(self, url: QUrl, category: SoundCategory) -> List[QSoundEffect]:
        """
        load multiple sound instances for a category based on polyphony configuration.
        
        :param url: URL of the sound file to load
        :type url: QUrl
        :param category: Sound category for the instances
        :type category: SoundCategory
        :return: List of loaded sound instances
        :rtype: List[QSoundEffect]
        """

        categoryConfig = self.soundCategories[category]
        
        loadMax = max(1, categoryConfig.maxPolyphony)
        soundInstances = []

        for _i in range(loadMax):
            soundInstance = QSoundEffect(self)
            soundInstance.setSource(url)

            volume = self._getEffectiveVolume(
                categoryConfig.volume,
                categoryConfig.muted
            )

            soundInstance.setVolume(volume)
            soundInstances.append(soundInstance)
        
        return soundInstances

    def _getEffectiveVolume(self, volume: float, isMuted: bool) -> float:
        """
        calculate the effective volume considering master mute and category mute status.
        
        :param volume: The requested volume
        :type volume: float
        :param isMuted: Whether the category is muted
        :type isMuted: bool
        :return: The effective volume to apply
        :rtype: float
        """

        if self.masterMuted or isMuted:
            return 0.0

        return clamp(volume * self.masterVolume, VOLUME_RANGE)

    def _getCategoryByEnum(self, category: SoundCategory) -> CategoryConfig:
        """
        get category configuration by enum.
        
        :param category: Sound category enum
        :type category: SoundCategory
        :return: Configuration for the category
        :rtype: CategoryConfig
        """

        return self.soundCategories[category]

    def _updateCategoryHandler(self, category: SoundCategory) -> None:
        """
        update volume of all instances in a category.
        
        :param category: Sound category to update
        :type category: SoundCategory
        """

        categoryConfig = self._getCategoryByEnum(category)

        volume = self._getEffectiveVolume(
            categoryConfig.volume,
            categoryConfig.muted
        )

        for (cachedCategory, _path), soundInstances in self.soundCache.items():
            if cachedCategory != category:
                continue

            for soundInstance in soundInstances:
                soundInstance.setVolume(volume)

    def _updateAllCategoryHandlers(self) -> None:
        """
        update volume of all loaded sound instances.
        """

        for cat in {cat for (cat, _p) in self.soundCache.keys()}:
            self._updateCategoryHandler(cat)

        # seperate for ambient audio
        ambientCategoryConfig = self.soundCategories[SoundCategory.AMBIENT]

        self.ambientAudioOutput.setVolume(
            self._getEffectiveVolume(
                ambientCategoryConfig.volume,
                ambientCategoryConfig.muted
            )
        )
    
    def _cleanupAll(self) -> None:
        """
        clean up and stop all sounds and timers.
        """

        # stop all scheduled sounds
        for timer in self.scheduledSounds:
            timer.stop()
        
        self.scheduledSounds.clear()

        # stop everything else
        self.stopAmbientAudio()

        for soundInstances in self.soundCache.values():
            for soundInstance in soundInstances:
                soundInstance.stop()
        
        self.soundCache.clear()

    def _now(self) -> int:
        """
        get current time in milliseconds since epoch.
        
        :return: Current milliseconds since epoch
        :rtype: int
        """

        return int(
            QDateTime.currentMSecsSinceEpoch()
        )

    # master mix methods
    @property
    def isMasterMuted(self) -> bool:
        """
        check if master mute is enabled.
        
        :return: True if master is muted, False otherwise
        :rtype: bool
        """

        return self.masterMuted

    def setMasterVolume(
        self,
        volume: Annotated[float, VOLUME_RANGE]
    ) -> None:
        """
        set the master volume level.
        
        :param volume: Volume level between 0.0 and 1.0
        :type volume: Annotated[float, VOLUME_RANGE]
        """

        self.masterVolume = clamp(volume, VOLUME_RANGE)
        self._updateAllCategoryHandlers()
    
    def setMasterMuted(self, muted: bool) -> None:
        """
        set the master mute state.
        
        :param muted: True to mute, False to unmute
        :type muted: bool
        """

        self.masterMuted = muted
        self.mutedSignal.emit(muted)
        self._updateAllCategoryHandlers()
    
    def toggleMasterMuted(self) -> None:
        """
        toggle the master mute state.
        """

        self.setMasterMuted(not self.masterMuted)

    # category methods
    def setCategoryVolume(
        self,
        category: SoundCategory | str,
        volume: Annotated[float, VOLUME_RANGE]
    ) -> None:
        """
        set volume for a sound category.
        
        :param category: Sound category or category name string
        :type category: SoundCategory | str
        :param volume: Volume level between 0.0 and 1.0
        :type volume: Annotated[float, VOLUME_RANGE]
        """

        if isinstance(category, str):
            category = SoundCategory[category.upper()]

        self.soundCategories[category].volume = clamp(volume, VOLUME_RANGE)
        self._updateCategoryHandler(category)
    
    def setCategoryMuted(
        self,
        category: SoundCategory,
        muted: bool
    ) -> None:
        """
        set mute state for a sound category.
        
        :param category: Sound category to mute
        :type category: SoundCategory
        :param muted: True to mute, False to unmute
        :type muted: bool
        """

        self.soundCategories[category].muted = muted
        self._updateCategoryHandler(category)
    
    # playback methods
    def preloadSounds(self, relativePath: str, category: SoundCategory) -> None:
        """
        preload sound instances for a file path and category.
        
        :param relativePath: Relative path to the sound file
        :type relativePath: str
        :param category: Sound category for the instances
        :type category: SoundCategory
        """

        key = (category, relativePath)

        if key in self.soundCache:
            return
    
        fullPath = self.soundAssets.getAsset(relativePath)
        url = QUrl.fromLocalFile(str(fullPath))
        self.soundCache[key] = self._massLoadSoundInstanceToCategory(url, category)
        
    def playSound(
        self,
        relativePath: str,
        category: SoundCategory,
        volume: Optional[float] = None,
        onFinish: Optional[Callable[[], None]] = None,
        finishDelay: int = 0
    ) -> None:
        """
        play a sound from file with optional volume and callback.
        
        :param relativePath: Relative path to the sound file
        :type relativePath: str
        :param category: Sound category for playback
        :type category: SoundCategory
        :param volume: Optional volume override (0.0 to 1.0)
        :type volume: Optional[float]
        :param onFinish: Optional callback when sound finishes
        :type onFinish: Optional[Callable[[], None]]
        :param finishDelay: Delay in milliseconds before calling onFinish
        :type finishDelay: int
        """

        key = (category, relativePath)
        
        # cooldown check
        categoryConfig = self.soundCategories[category]
        categoryCooldown = categoryConfig.audioCooldown

        if categoryCooldown > 0:
            timeNow = self._now()
            timePlayed = self.cooldownCache.get(key, -10**9)
            delta = timeNow - timePlayed

            if delta < (categoryCooldown * 1000):
                return
            
            self.cooldownCache[key] = timeNow
        
        # check cache
        if key not in self.soundCache:
            self.preloadSounds(relativePath, category)
        
        # get a free instance or do a robbery
        soundInstances = self.soundCache[key]
        soundInstance = None

        for instance in soundInstances:
            if not instance.isPlaying():
                soundInstance = instance
                break

        if soundInstance is None:
            soundInstance = soundInstances[0]

        # set volume if provided
        callVolume = clamp(volume, VOLUME_RANGE) if volume is not None else 1.0

        effectiveVolume = self._getEffectiveVolume(
            categoryConfig.volume * callVolume,
            categoryConfig.muted
        )

        soundInstance.setVolume(effectiveVolume)

        # playback and finish handler
        def playingChangeHandler():
            if soundInstance.isPlaying():
                return                
            
            soundInstance.playingChanged.disconnect(playingChangeHandler)

            if finishDelay > 0:
                QTimer.singleShot(
                    finishDelay,
                    onFinish
                )
            else:
                onFinish()

        if onFinish:
            soundInstance.playingChanged.connect(playingChangeHandler)

        soundInstance.play()
        return soundInstance
    
    # audio playback
    def isAmbientPlaying(self) -> bool:
        """
        check if ambient audio is currently playing.
        
        :return: True if ambient audio is playing
        :rtype: bool
        """

        return self.ambientMediaPlayer.playbackState() == QMediaPlayer.PlayingState

    def playAmbientAudio(self, relativePath: str) -> None:
        """
        play ambient audio that loops continuously.
        
        :param relativePath: Relative path to the audio file
        :type relativePath: str
        """

        if self.isAmbientPlaying():
            return

        categoryConfig = self.soundCategories[SoundCategory.AMBIENT]
        fullPath = self.soundAssets.getAsset(relativePath + ".wav")
        url = QUrl.fromLocalFile(str(fullPath))

        self.ambientMediaPlayer.setSource(url)
        self.ambientAudioOutput.setVolume(
            self._getEffectiveVolume(
                categoryConfig.volume,
                categoryConfig.muted
            )
        )
        self.ambientMediaPlayer.play()

    def stopAmbientAudio(self) -> None:
        """
        stop the currently playing ambient audio.
        """

        self.ambientMediaPlayer.stop()
        self.ambientMediaPlayer.setSource(QUrl())

    # speech blip playback
    def playSpeechBlip(self) -> None:
        """
        play a random speech blip sound.
        """

        index = random.randint(0, SPEECH_BLIP_COUNT - 1)
        key = (SoundCategory.SPEECH, f"_blip_{index}")
        
        effects = self.soundCache.get(key)

        if effects and len(effects) > 0:
            effects[0].play()

    # scheduled sounds
    def scheduleTimedSound(
        self,
        intervalMs: int,
        relativePath: str,
        category: SoundCategory
    ) -> None:
        """
        schedule a sound to repeat at regular intervals.
        
        :param intervalMs: Interval in milliseconds between plays
        :type intervalMs: int
        :param relativePath: Relative path to the sound file
        :type relativePath: str
        :param category: Sound category for playback
        :type category: SoundCategory
        """

        scheduledTimer = QTimer(self)
        scheduledTimer.setInterval(max(10, intervalMs))

        scheduledTimer.timeout.connect(
            lambda: self.playSound(relativePath, category)
        )
        scheduledTimer.start()

        self.scheduledSounds.append(scheduledTimer)
        return scheduledTimer

    # cleanup
    def shutdown(self) -> None:
        """
        shutdown the sound manager and clean up resources.
        """

        self._cleanupAll()
