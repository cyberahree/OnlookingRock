from ..context import EventContext
from ..base import BaseEvent

from PySide6.QtCore import QTimer
from typing import Callable

import requests

class MotivationEvent(BaseEvent):
    id = "motivation"
    weight = 0.7
    cooldownSeconds = 400

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

        response = requests.get("https://quotes-api-self.vercel.app/quote", timeout=5)

        quote = "whatever happens, dont forget to stay positive! :D"
        author = "rockin' (i couldnt find anything else motivational)"

        if response.ok:
            quoteData = response.json()
            
            quote = quoteData.get("quote", quote).lower()
            author = quoteData.get("author", author).lower()

        duration = context.speech.addSpeech(
            f"{quote} -{author}"
        )

        QTimer.singleShot(duration + 150, lambda: self.lock.release() or self.onFinished())


EVENTS = [
    MotivationEvent()
]
