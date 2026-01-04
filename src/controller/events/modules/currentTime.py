from ..context import EventContext
from ..base import BaseEvent

from PySide6.QtCore import QTimer

from datetime import datetime
from typing import Callable

import random

class TimeEvent(BaseEvent):
    id = "time"
    weight = 0.9
    cooldownSeconds = 500

    def canRun(self, context: EventContext) -> bool:
        if len(context.speech.queue) > 0 or context.speech.active:
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
            "petting"
        )

        duration = context.speech.addSpeech(
            self.getTimePhrase()
        )

        QTimer.singleShot(duration + 150, lambda: self.lock.release() or self.onFinished())

    def getTimePhrase(self):
        """Get a time-appropriate phrase based on current hour."""
        hour = datetime.now().hour
        
        morning_phrases = [
            "good morning! hope you're having a productive start!",
            "early bird catches the worm, i see!",
            "fresh start to the day, let's make it count!",
            "rise and shine! time to get things done!",
            "morning grind, let's go!",
        ]
        
        afternoon_phrases = [
            "afternoon slump? time for a break maybe?",
            "halfway through the day, you're doing great!",
            "remember to stay hydrated!",
            "keep up the great work this afternoon!",
            "afternoon hustle, almost there!",
        ]
        
        evening_phrases = [
            "burning the midnight oil i see!",
            "evening session, almost time to rest soon?",
            "time flies when you're focused!",
            "don't forget to unwind before bed!",
        ]
        
        if 5 <= hour < 12:
            return random.choice(morning_phrases)
        elif 12 <= hour < 17:
            return random.choice(afternoon_phrases)
        else:
            return random.choice(evening_phrases)


EVENTS = [
    TimeEvent()
]
