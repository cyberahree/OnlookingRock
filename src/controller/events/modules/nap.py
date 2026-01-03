from PySide6.QtCore import QTimer

from ..base import BaseEvent

class NapEvent(BaseEvent):
    id = "nap"
    weight = 1.0
    cooldownSeconds = 120

    def canRun(self, context) -> bool:
        # don't start if user is currently dragging or interacting heavily
        try:
            if context.sprite.dragger.isDragging:
                return False
        except Exception:
            pass

        return True

    def run(
        self,
        context,
        onFinished
    ):
        lock = context.lock(self.id, "drag", "eyetrack", "petting", "blink", "autopilot")

        try:
            context.sprite.dragger.reset()
        except Exception:
            pass

        try:
            context.sprite.updateSpriteFeatures("idle", "sleepy", True)
        except Exception:
            pass

        try:
            context.speech.addSpeech("zzz...")
        except Exception:
            pass

        def finish():
            lock.release()
            onFinished()

        QTimer.singleShot(4000, finish)

EVENTS = [NapEvent()]
