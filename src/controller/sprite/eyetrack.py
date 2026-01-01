from PySide6.QtCore import QPoint, QPointF
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QCursor

from typing import Callable

class LaserMouseController:
    def __init__(
        self,
        sprite: QWidget,
        canTrack: Callable[[], bool],
        minDistance: int = 1024,
        maxOffset: int = 8,
        smoothing: float = 0.4,
    ):
        self.sprite = sprite
        self.canTrack = canTrack
        self.offset = QPointF(0.0, 0.0)

        self.minDistance = minDistance
        self.maxOffset = maxOffset
        self.smoothing = smoothing

    def _clamp(self, value: float, minValue: float, maxValue: float) -> float:
        return max(minValue, min(value, maxValue))

    def _computeTarget(self, mousePosition: QPoint) -> QPointF:
        mouseX = float(mousePosition.x())
        mouseY = float(mousePosition.y())

        distance = (mouseX ** 2 + mouseY ** 2) ** 0.5

        if distance >= self.minDistance:
            return QPointF(0.0, 0.0)
        
        # div by zero <3
        if distance < 1e-6:
            return QPointF(0.0, 0.0)
        
        # squared to ease out
        t = (1.0 - (distance / self.minDistance)) ** 2

        strength = t * self.maxOffset
        scale = self.sprite.currentSpriteScale

        return QPointF(
            self._clamp((mouseX / distance) * strength, -self.maxOffset, self.maxOffset) * scale,
            self._clamp((mouseY / distance) * strength, -self.maxOffset, self.maxOffset) * scale
        )

    def update(self):
        eyesLabel = self.sprite.eyesLabel

        if not self.canTrack():
            eyesLabel.move(0, 0)
            return

        mousePosition = self.sprite.mapFromGlobal(
            QCursor.pos()
        )

        centerPosition = QPoint(
            eyesLabel.width() // 2,
            eyesLabel.height() // 2
        )

        directionVector = QPointF(
            mousePosition.x() - centerPosition.x(),
            mousePosition.y() - centerPosition.y()
        )

        distance = (directionVector.x() ** 2 + directionVector.y() ** 2) ** 0.5
        target = QPointF(0, 0)

        if distance < self.minDistance:
            target = self._computeTarget(directionVector)
        
        # smooth movement
        self.offset = QPointF(
            self.offset.x() + (target.x() - self.offset.x()) * self.smoothing,
            self.offset.y() + (target.y() - self.offset.y()) * self.smoothing,
        )

        eyesLabel.move(
            int((self.sprite.width() - eyesLabel.width()) / 2 + self.offset.x()),
            int((self.sprite.height() - eyesLabel.height()) / 2 + self.offset.y())
        )
