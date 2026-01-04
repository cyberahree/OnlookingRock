from ..context import EventContext
from ..base import BaseEvent

from PySide6.QtCore import QTimer
from typing import Callable

import random


class TimeEvent(BaseEvent):
    id = "time"
    weight = 0.45
    cooldownSeconds = 500

    time_phrases = [
        "Time flies when you're having fun!",
        "Remember, time is precious, use it wisely.",
        "It's a great time to take a break!",
        "Time for a quick stretch perhaps?",
        "The day is almost halfway through!",
        "Time management is key to success.",
        "It's been quite a journey today!",
    ]

    def canRun(self, context: EventContext) -> bool:
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

        duration = context.speech.addSpeech(
            random.choice(self.time_phrases)
        )

        QTimer.singleShot(duration + 150, lambda: self.lock.release() or self.onFinished())

EVENTS = [
    TimeEvent()
]
