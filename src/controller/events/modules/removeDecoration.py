from ..context import EventContext
from ..base import BaseEvent

from PySide6.QtCore import QTimer, QPointF
from PySide6.QtGui import QGuiApplication

from typing import Callable

import math

class RemoveDecorationEvent(BaseEvent):
    id = "removeDecoration"
    weight = 0.05
    cooldownSeconds = 600

    def canRun(self, context: EventContext) -> bool:
        # add your logic here
        if len(context.scene.getEntities()) < 1:
            return False
        
        if len(context.speech.queue) > 0:
                return False
        return True

    def run(
        self,
        context: EventContext,
        onFinished: Callable[[], None]
    ):
        self.context = context
        self.onFinished = onFinished
        self.lock = context.lock(
            self.id,
            "drag",
            "eyetrack",
            "petting",
            "blink",
            "autopilot",
            "startmenu"
        )

        self.randomDecoration = context.scene.getNearestEntityFromPoint(
            context.scene.getSpriteCentre()
        )

        target = self.determineBestPosition()

        context.animateSpriteTo(
            target,
            onFinished= lambda: self.context.delayMs(1200, self.placeSkip)
        )

    def determineBestPosition(self):
        # if the decoration is in a quadrant, the best position would be away from the
        # edge of the quadrant and closer to the centre of the screen
        actionViewport = self.context.sceneSystem.getViewportAtPoint(
            QPointF(self.randomDecoration.x, self.randomDecoration.y)
        )

        decorationPosition = QPointF(
            self.randomDecoration.x,
            self.randomDecoration.y
        )

        decorationWidth, decorationHeight = self.context.sceneSystem.getDecorationSize(
            self.randomDecoration.name
        )

        spriteWidth, spriteHeight = self.context.sprite.width(), self.context.sprite.height()

        decorationCenter = QPointF(
            decorationPosition.x() + decorationWidth / 2,
            decorationPosition.y() + decorationHeight / 2
        )

        viewportBounds = actionViewport.globalBounds()
    
        viewportCenter = QPointF(
            (viewportBounds.left() + viewportBounds.right()) / 2,
            (viewportBounds.top() + viewportBounds.bottom()) / 2
        )

        directionX = viewportCenter.x() - decorationCenter.x()
        directionY = viewportCenter.y() - decorationCenter.y()
        
        magnitude = math.sqrt(directionX ** 2 + directionY ** 2)

        if magnitude > 0:
            directionX /= magnitude
            directionY /= magnitude
        
        maxDecorationBound = max(decorationWidth, decorationHeight) / 2
        maxSpriteBound = max(spriteWidth, spriteHeight) / 2
        minDistance = maxDecorationBound + maxSpriteBound + 32
        
        # Position sprite at minimum distance in direction of center
        targetPosition = QPointF(
            decorationCenter.x() + directionX * minDistance,
            decorationCenter.y() + directionY * minDistance
        )

        return targetPosition

    def placeSkip(self):
        duration = self.context.speech.addSpeech(
            f"this {self.randomDecoration.name.replace('_', ' ')} looks a bit out of place..",
            5400
        )
        self.context.yieldMs(duration + 150)

        duration = self.context.speech.addSpeech("let me just remove it quickly!", 1750)
        skipId = self.context.scene.spawnEntity(
            "skip",
            self.context.scene.getSpriteCentre() - QPointF(50, 0)
        )
        self.context.yieldMs(duration + 150)

        self.context.scene.removeEntity(self.randomDecoration.entityId)
        self.context.sounds.playSound("bin.wav")

        self.context.yieldMs(450)
        duration = self.context.speech.addSpeech("there we go!", 2250)
        self.context.yieldMs(duration + 150)

        self.context.scene.removeEntity(skipId)
        duration = self.context.speech.addSpeech("it looks beautiful now, doesn't it? ^^", 5000)
        self.context.yieldMs(duration + 150)

        QTimer.singleShot(120, lambda: self.lock.release() or self.onFinished())

EVENTS = [
    RemoveDecorationEvent()
]
