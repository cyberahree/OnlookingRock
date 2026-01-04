from ...sprite.animation import FacialAnimationSequence
from ..context import EventContext
from ..base import BaseEvent

from PySide6.QtCore import QTimer

from typing import Callable
from random import randint

class NapEvent(BaseEvent):
    id = "nap"
    weight = 0.6
    cooldownSeconds = 120

    def canRun(self, context: EventContext) -> bool:
        # don't start if user is currently dragging or interacting heavily
        try:
            if context.sprite.dragger.isDragging:
                return False
            
            if len(context.speech.queue) > 0:
                return False
        except Exception:
            pass

        return True

    def run(
        self,
        context: EventContext,
        onFinished: Callable[[], None]
    ):
        lock = context.lock(
            self.id,
            "drag",
            "eyetrack",
            "petting",
        )

        sleepDuration = randint(4000, 7000)

        try:
            context.sprite.dragger.reset()
        except Exception:
            pass

        try:
            context.sprite.updateSpriteFeatures("idle", "sleepy", True)
        except Exception:
            pass

        try:
            context.speech.addSpeech("zzz...", sleepDuration)
        except Exception:
            pass

        def onSleepFinish():
            # perform rapid blinking animation to simulate waking up
            sequence = FacialAnimationSequence(context.sprite)
            
            # 6 rapid blinks with 100ms intervals
            for _ in range(6):
                sequence.addState(
                    randint(50, 250),
                    eyes="blink",
                    face="idle"
                )

                sequence.addState(
                    randint(150, 200),
                    eyes="idle",
                    face="idle"
                )

            # return to normal appearance
            sequence.addState(0, face="idle", eyes="idle")
            
            def on_wakeup_complete():
                lock.release()
                onFinished()
            
            sequence.play(on_wakeup_complete)

        QTimer.singleShot(sleepDuration, onSleepFinish)

EVENTS = [
    NapEvent()
]
