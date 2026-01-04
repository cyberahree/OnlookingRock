from ..context import EventContext
from ..base import BaseEvent

from PySide6.QtCore import QTimer
from typing import Callable

import random

class RandomThoughtEvent(BaseEvent):
    id = "randomThought"
    weight = 1.0
    cooldownSeconds = 350

    random_thoughts = [
        "i wonder what you're working on right now",
        "wouldn't it be nice to take a walk?",
        "i'm curious about what you think of today",
        "sometimes the best ideas come when you're relaxing",
        "have you had enough water today?",
        "i bet you're doing something interesting!",
        "random thought: what's your favorite color?",
        "i hope you're having a good day so far",
        "sometimes it's good to just pause and reflect",
        "you know what? you're pretty cool :>"
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
            random.choice(self.random_thoughts)
        )

        QTimer.singleShot(duration + 150, lambda: self.lock.release() or self.onFinished())

EVENTS = [
    RandomThoughtEvent()
]
