from ..asset import AssetController

from .speech import buildSpeechBlips

from PySide6.QtMultimedia import QSoundEffect, QMediaPlayer, QAudioOutput
from PySide6.QtCore import QObject, QUrl, QTimer, Signal, QDateTime

from typing import List, Optional, Annotated
from dataclasses import dataclass
from enum import Enum

import random

SPEECH_BLIP_COUNT = 6

class SoundCategory(Enum):
    EVENT = 0
    FEEDBACK = 1
    AMBIENT = 2
    SPECIAL = 3
    SPEECH = 4

@dataclass
class ValueRange:
    min: float = 0.0
    max: float = 1.0

@dataclass
class CategoryConfig:
    volume: float = 1.0
    muted: bool = False
    maxPolyphony: int = 3
    audioCooldown: int = 0 # in seconds, how long until one sound can be played again

VOLUME_RANGE = ValueRange()

def clamp(value: float, range: ValueRange) -> float:
    return max(range.min, min(range.max, value))

class SoundManager(QObject):
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

        self.soundAssets = AssetController("sounds")

        self.mutedSignal = Signal(bool)
        self.masterMuted = False
        self.masterVolume = 1.0

        self.soundCategories = {
            SoundCategory.EVENT: CategoryConfig(maxPolyphony=9),
            SoundCategory.FEEDBACK: CategoryConfig(),
            SoundCategory.AMBIENT: CategoryConfig(),
            SoundCategory.SPECIAL: CategoryConfig(),
            SoundCategory.SPEECH: CategoryConfig(maxPolyphony=SPEECH_BLIP_COUNT),
        }

        self.soundCache = {}
        self.cooldownCache = {}

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
    def _massLoadSoundInstanceToCategory(self, url: QUrl, category: SoundCategory) -> List[QSoundEffect]:
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
        if self.masterMuted or isMuted:
            return 0.0

        return clamp(volume * self.masterVolume, VOLUME_RANGE)

    def _updateCategoryHandler(self, category: SoundCategory) -> None:
        categoryConfig = self.soundCategories[category]
        volume = self._getEffectiveVolume(
            categoryConfig.volume,
            categoryConfig.muted
        )

        categorySoundInstances = self.soundCache.get(category, [])
        for soundInstance in categorySoundInstances:
            soundInstance.setVolume(volume)

    def _updateAllCategoryHandlers(self) -> None:
        for (category, _path) in self.soundCache.keys():
            self._updateCategoryHandler(category)
        
        # seperate for ambient audio
        ambientCategoryConfig = self.soundCategories[SoundCategory.AMBIENT]

        self.ambientAudioOutput.setVolume(
            self._getEffectiveVolume(
                ambientCategoryConfig.volume,
                ambientCategoryConfig.muted
            )
        )
    
    def _cleanupAll(self) -> None:
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
        return int(
            QDateTime.currentMSecsSinceEpoch()
        )

    # master mix methods
    @property
    def isMasterMuted(self) -> bool:
        return self.masterMuted

    def setMasterVolume(
        self,
        volume: Annotated[float, VOLUME_RANGE]
    ) -> None:
        self.masterVolume = clamp(volume, VOLUME_RANGE)
        self._updateAllCategoryHandlers()
    
    def setMasterMuted(self, muted: bool) -> None:
        self.masterMuted = muted
        self.mutedSignal.emit(muted)
        self._updateAllCategoryHandlers()
    
    def toggleMasterMuted(self) -> None:
        self.setMasterMuted(not self.masterMuted)

    # category methods
    def setCategoryVolume(
        self,
        category: SoundCategory,
        volume: Annotated[float, VOLUME_RANGE]
    ) -> None:
        self.soundCategories[category].volume = clamp(volume, VOLUME_RANGE)
        self._updateCategoryHandler(category)
    
    def setCategoryMuted(
        self,
        category: SoundCategory,
        muted: bool
    ) -> None:
        self.soundCategories[category].muted = muted
        self._updateCategoryHandler(category)
    
    # playback methods
    def preloadSounds(self, relativePath: str, category: SoundCategory) -> None:
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
        onFinish: Optional[callable] = None,
        finishDelay: int = 0
    ) -> None:
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
    def playAmbientAudio(self, relativePath: str) -> None:
        categoryConfig = self.soundCategories[SoundCategory.AMBIENT]
        fullPath = self.soundAssets.getAsset(relativePath)
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
        self.ambientMediaPlayer.stop()

    # speech blip playback
    def playSpeechBlip(self) -> None:
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
        self._cleanupAll()
