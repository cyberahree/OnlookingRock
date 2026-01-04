from ..context import EventContext
from ..base import BaseEvent

from PySide6.QtCore import QTimer
from typing import Callable

import requests

class JokeEvent(BaseEvent):
    id = "joke"
    weight = 0.8
    cooldownSeconds = 450

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
            "autopilot"
        )

        response = requests.get("https://official-joke-api.appspot.com/random_joke", timeout=5)

        setup = "why did the joke API fail? .."
        punchline = "it was having a bad request day! ahah! i know, so funny 8)"
        
        if response.ok:
            jokeData = response.json()
            setup = jokeData.get("setup", "").lower()
            punchline = jokeData.get("punchline", "").lower()        

        totalDuration = 0

        self.context.sprite.updateSpriteFeatures(
            "idle", "petting", True
        )

        totalDuration += self.context.speech.addSpeech(setup)
        totalDuration += self.context.speech.addSpeech(punchline)

        QTimer.singleShot(totalDuration + 500, self.cleanup)

    def cleanup(self):
        self.context.sprite.updateSpriteFeatures(
            "idle", "idle", False
        )

        self.lock.release()
        self.onFinished()

EVENTS = [
    JokeEvent()
]
