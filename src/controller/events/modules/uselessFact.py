from ..context import EventContext
from ..base import BaseEvent

from PySide6.QtCore import QTimer
from typing import Callable

import requests

class UselessFactEvent(BaseEvent):
    id = "uselessFact"
    weight = 0.95
    cooldownSeconds = 300

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
            "petting",
        )

        fact = "i tried to get one, but i couldn't"

        response = requests.get("https://uselessfacts.jsph.pl/api/v2/facts/random", timeout=5)

        if response.ok:
            fact = response.json().get("text", "i couldnt understand what the fact was.. :<").lower()

        duration = self.context.speech.addSpeech(fact)
        QTimer.singleShot(duration + 150, lambda: self.lock.release() or self.onFinished())

EVENTS = [
    UselessFactEvent()
]
