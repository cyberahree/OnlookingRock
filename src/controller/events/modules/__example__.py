from ..context import EventContext
from ..base import BaseEvent

from PySide6.QtCore import QTimer

from typing import Callable

class ExampleEvent(BaseEvent):
    id = "example"
    name = "Example Event"

    weight = 1.0
    cooldownSeconds = 120

    def canRun(self, context: EventContext) -> bool:
        # add your logic here
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
            "autopilot"
        )

        QTimer.singleShot(120, lambda: self.lock.release() or self.onFinished())

EVENTS = [
    ExampleEvent()
]
