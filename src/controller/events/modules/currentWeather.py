from ...sprite.templates import (
    WEATHER_TEMPERATURE_TEMPLATES,
    WEATHER_VISIBILITY_TEMPLATES,
    WEATHER_PRECIPITATION_TEMPLATES,
    pickRandom
)

from ..context import EventContext
from ..base import BaseEvent

from PySide6.QtCore import QTimer
from typing import Callable

class WeatherEvent(BaseEvent):
    id = "weather"
    weight = 0.35
    cooldownSeconds = 7200

    def canRun(self, context: EventContext) -> bool:
        if len(context.speech.queue) > 0:
            return False
        
        locationServices = context.sprite.locationServices

        if not locationServices.getLocation():
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

        locationServices = context.sprite.locationServices
        weatherData = locationServices.getWeatherData()

        messages = [
            pickRandom(
                WEATHER_TEMPERATURE_TEMPLATES
            ).format(weatherData.temperature),

            pickRandom(
                WEATHER_VISIBILITY_TEMPLATES
            ).format(weatherData.visibility),

            pickRandom(
                WEATHER_PRECIPITATION_TEMPLATES
            ).format(
                amount = weatherData.precipitation,
                chance = weatherData.precipitationChance
            )
        ]

        # pick in a random order
        speechDuration = 0

        for _ in range(len(messages)):
            message = pickRandom(messages)
            messages.remove(message)

            speechDuration += (context.speech.addSpeech(message) + 150)

        QTimer.singleShot(speechDuration, lambda: self.lock.release() or self.onFinished())


EVENTS = [
    WeatherEvent()
]
