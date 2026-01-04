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

import time

class WeatherEvent(BaseEvent):
    id = "weather"
    weight = 0.35
    cooldownSeconds = 7200

    def canRun(self, context: EventContext) -> bool:
        if len(context.speech.queue) > 0:
            return False
        
        locationServices = context.sprite.locationServices

        if not locationServices.locationPermissionAllowed():
            return False

        return True

    def run(
        self,
        context: EventContext,
        onFinished: Callable[[], None]
    ):
        # TODO: fix
        self.context = context
        self.onFinished = onFinished
        self.lock = context.lock(
            self.id,
            "petting"
        )

        locationServices = context.sprite.locationServices
        weatherData = locationServices.getWeatherData()

        if weatherData is None or not weatherData.timestamps:
            self.lock.release()
            self.onFinished()
            return

        # find the current hour's weather data
        currentTime = int(time.time())
        closestIndex = 0
        minDiff = abs(weatherData.timestamps[0] - currentTime)

        for i, timestamp in enumerate(weatherData.timestamps):
            diff = abs(timestamp - currentTime)
            if diff < minDiff:
                minDiff = diff
                closestIndex = i

        # extract current hour's values
        currentTemp = round(weatherData.temperature[closestIndex], 1)
        currentVisibility = int(weatherData.visibility[closestIndex])
        currentPrecipitation = round(weatherData.precipitation[closestIndex], 1)
        currentPrecipChance = weatherData.precipitationChance[closestIndex]

        messages = [
            pickRandom(
                WEATHER_TEMPERATURE_TEMPLATES
            ).format(currentTemp),

            pickRandom(
                WEATHER_VISIBILITY_TEMPLATES
            ).format(currentVisibility),

            pickRandom(
                WEATHER_PRECIPITATION_TEMPLATES
            ).format(
                amount=currentPrecipitation,
                chance=currentPrecipChance
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
