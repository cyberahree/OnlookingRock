from __future__ import annotations

from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QWidget

from collections import deque
from typing import Callable, Deque, Optional, Tuple

import math
import time

# unwrap angle delta to [-pi, pi] to avoid jumps at the -pi/+pi boundary.
def unwrapDelta(dtheta: float) -> float:
    while dtheta > math.pi:
        dtheta -= 2 * math.pi

    while dtheta < -math.pi:
        dtheta += 2 * math.pi

    return dtheta

# this class detects a circular "petting" gesture anywhere on the sprite
# this is done by:
# - collecting cursor samples while the cursor is over the sprite
# - estimating a centre from the samples determining a centroid,
# - and measuring angular travel around that centre
# - if total signed rotation reaches roughlty one full turn
#   in either direction, we treat it as a petting loop
class CircularPettingController:
    def __init__(
        self,
        sprite: QWidget,
        canPet: Callable[[], bool] = lambda: True,

        # detection tuning
        windowMs: int = 900,
        maxSampleGapMs: int = 90,
        loopsRequired: float = 0.90,

        # small guards against noise: lower to allow for smaller circles
        minPathPxAtScale1: float = 25.0,
        minMeanRadiusPxAtScale1: float = 4.0,
        maxRadiusStdRatio: float = 0.55,

        # output behavior
        holdMs: int = 950,
        cooldownMs: int = 600,
    ):
        self.sprite = sprite
        self.canPet = canPet

        self.windowMs = windowMs
        self.maxSampleGapMs = maxSampleGapMs
        self.loopsRequired = loopsRequired

        self.minPathPxAtScale1 = minPathPxAtScale1
        self.minMeanRadiusPxAtScale1 = minMeanRadiusPxAtScale1
        self.maxRadiusStdRatio = maxRadiusStdRatio

        self.holdMs = holdMs
        self.cooldownMs = cooldownMs

        self._samples: Deque[Tuple[float, float, float]] = deque()  # (x, y, t_ms)
        self._pettingUntilMs: float = 0.0
        self._lastTriggerMs: float = -1e12
        self._lastSampleMs: Optional[float] = None

    def reset(self) -> None:
        self._samples.clear()
        self._lastSampleMs = None

    def nowMs(self) -> float:
        return time.time() * 1000.0

    @property
    def spriteScale(self) -> float:
        # sprite has `currentSpriteScale`.
        return float(getattr(self.sprite, "currentSpriteScale", 1.0))

    def isPetting(self) -> bool:
        return self.nowMs() <= self._pettingUntilMs

    def update(self) -> bool:
        # sample cursor and update petting detection state.
        # returns True if the sprite should be considered "petting" right now.
        now = self.nowMs()

        if not self.canPet():
            self.reset()
            self._pettingUntilMs = 0.0
            return False

        # map cursor to sprite-local
        local = self.sprite.mapFromGlobal(QCursor.pos())

        cursorX = float(local.x())
        cursorY = float(local.y())

        # the cursor must be over the sprite
        withinX = (0.0 <= cursorX <= float(self.sprite.width()))
        withinY = (0.0 <= cursorY <= float(self.sprite.height()))
        
        if not (withinX and withinY):
            self.reset()
            return self.isPetting()

        # reset if sampling gap is too large (teleport / hitch)
        if (self._lastSampleMs is not None) and ((now - self._lastSampleMs) > self.maxSampleGapMs):
            self.reset()

        self._lastSampleMs = now
        self._samples.append((cursorX, cursorY, now))

        # drop samples outside our time window
        cutoff = now - float(self.windowMs)

        while self._samples and self._samples[0][2] < cutoff:
            self._samples.popleft()

        if self._checkCircle(now):
            self._pettingUntilMs = now + float(self.holdMs)

        return self.isPetting()

    def _checkCircle(self, now: float) -> bool:
        if (now - self._lastTriggerMs) < float(self.cooldownMs):
            return False

        if len(self._samples) < 12:
            return False

        scale = self.spriteScale

        # estimate a centroid
        sampleXs = [p[0] for p in self._samples]
        sampleYs = [p[1] for p in self._samples]

        centroidX = sum(sampleXs) / len(sampleXs)
        centroidY = sum(sampleYs) / len(sampleYs)

        # angles + radii around centroid
        angles = []
        radii = []

        for x, y, _time in self._samples:
            deltaX = x - centroidX
            deltaY = y - centroidY

            angles.append(math.atan2(deltaY, deltaX))
            radii.append(math.hypot(deltaX, deltaY))

        meanRadius = sum(radii) / len(radii)

        if meanRadius < (float(self.minMeanRadiusPxAtScale1) * scale):
            return False

        radiusVariance = sum((rr - meanRadius) ** 2 for rr in radii) / len(radii)
        radiusStdDeviation = math.sqrt(radiusVariance)

        # radius consistency check, relative to size (so any size works)
        if (radiusStdDeviation / max(meanRadius, 1e-6)) > float(self.maxRadiusStdRatio):
            return False

        # path length (avoid false triggers on tiny jitter)
        path = 0.0
    
        for (x1, y1, _), (x2, y2, __) in zip(self._samples, list(self._samples)[1:]):
            path += math.hypot(x2 - x1, y2 - y1)

        if path < (float(self.minPathPxAtScale1) * scale):
            return False

        # signed rotation around centroid.
        signedRotation = 0.0

        # unwrap angles and sum deltas
        for a, b in zip(angles, angles[1:]):
            signedRotation += unwrapDelta(b - a)

        # check for enough loops
        if abs(signedRotation) >= (2.0 * math.pi * float(self.loopsRequired)):
            self._lastTriggerMs = now
            self.reset()
            return True

        return False
