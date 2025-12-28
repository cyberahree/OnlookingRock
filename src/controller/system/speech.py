from PySide6.QtCore import QTemporaryFile, QUrl
from PySide6.QtMultimedia import QSoundEffect

from typing import Any, List, TYPE_CHECKING

import struct
import math
import random

FADE_DURATION = 0.008  # seconds
SAMPLE_BIT_DEPTH = 16
CHANNELS = 1

# temp file references
_tempFileStorage: List[QTemporaryFile] = []


def generateBlipWav(
    frequency: float = 220.0,
    duration: float = 0.055,
    sampleRate: int = 44100,
) -> QTemporaryFile:
    samplesCount = int(sampleRate * duration)
    fadeLength = int(sampleRate * FADE_DURATION) 

    rawSamples = []

    for i in range(samplesCount):
        t = i / sampleRate
        phase = 2 * math.pi * frequency * t

        sample = 1.0 if math.sin(phase) >= 0 else -1.0

        envelope = 1.0
        if i < fadeLength:
            envelope = i / fadeLength
        elif i > samplesCount - fadeLength:
            envelope = (samplesCount - i) / fadeLength

        sample = sample * envelope

        intSample = int(sample * 32767)
        intSample = max(-32768, min(32767, intSample))
        rawSamples.append(intSample)

    # wav file construction
    byteRate = sampleRate * CHANNELS * SAMPLE_BIT_DEPTH // 8
    blockAlign = CHANNELS * SAMPLE_BIT_DEPTH // 8
    dataSize = samplesCount * CHANNELS * SAMPLE_BIT_DEPTH // 8

    wavData = bytearray()

    # RIFF chunk
    wavData.extend(b'RIFF')
    wavData.extend(struct.pack('<I', 36 + dataSize))
    wavData.extend(b'WAVE')

    # fmt chunk

    # order:
    # chunk size ,audio format, channel count
    # sample rate, byte rate, block align
    # bps

    wavData.extend(b'fmt ')
    wavData.extend(struct.pack('<I', 16))
    wavData.extend(struct.pack('<H', 1))
    wavData.extend(struct.pack('<H', CHANNELS))
    wavData.extend(struct.pack('<I', sampleRate))
    wavData.extend(struct.pack('<I', byteRate))
    wavData.extend(struct.pack('<H', blockAlign))
    wavData.extend(struct.pack('<H', SAMPLE_BIT_DEPTH))

    # data chunk
    wavData.extend(b'data')
    wavData.extend(struct.pack('<I', dataSize))

    for sample in rawSamples:
        wavData.extend(struct.pack('<h', sample))

    # write to temporary file
    tempWavFile = QTemporaryFile()
    if tempWavFile.open():
        tempWavFile.write(wavData)
        tempWavFile.flush()
        tempWavFile.seek(0)
        return tempWavFile

    raise RuntimeError("Failed to create temporary WAV file")

def buildSpeechBlips(
    soundController,
    speechCategory: Any,
    blipCount: int,
    baseFrequency: float = 220.0,
    pitchVariance: float = 0.25,
    duration: float = 0.055,
    sampleRate: int = 44100,
    volume: float = 0.5,
) -> None:
    global _tempFileStorage
    
    # clear existing temp files
    _tempFileStorage.clear()
    
    categoryConfig = soundController.soundCategories[speechCategory]
    effectiveVolume = soundController._getEffectiveVolume(
        categoryConfig.volume * volume,
        categoryConfig.muted
    )
    
    for i in range(blipCount):
        # calculate frequency with pitch spread
        pitchOffset = -pitchVariance + (2 * pitchVariance * i / (blipCount - 1))
        frequency = baseFrequency * (1.0 + pitchOffset)
        
        # generate WAV and get temp file
        tempFile = generateBlipWav(
            frequency=frequency,
            duration=duration,
            sampleRate=sampleRate
        )

        # keep reference to prevent deletion
        _tempFileStorage.append(tempFile)
        
        # create QSoundEffect for this blip
        effect = QSoundEffect(soundController)
        effect.setSource(QUrl.fromLocalFile(tempFile.fileName()))
        effect.setVolume(effectiveVolume)
        
        # register in sound cache with unique key
        key = (speechCategory, f"_blip_{i}")
        soundController.soundCache[key] = [effect]
