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
        closestIndex = 0
        currentTime = int(time.time())

        minDifference = abs(
            weatherData.timestamps[0] - currentTime
        )

        for index, timestamp in enumerate(weatherData.timestamps):
            timeDifference = abs(timestamp - currentTime)

            if timeDifference < minDifference:
                minDifference = timeDifference
                closestIndex = index

        # extract current hour's values
        currentTemperature = round(weatherData.temperature[closestIndex], 1)
        currentVisibility = int(weatherData.visibility[closestIndex])
        currentPrecipitation = round(weatherData.precipitation[closestIndex], 1)
        currentPrecipChance = weatherData.precipitationChance[closestIndex]

        # add speech commentary
        messages = [
            pickRandom(WEATHER_TEMPERATURE_TEMPLATES).format(
                value=currentTemperature,
                unit=weatherData.temperatureUnit
            ),

            pickRandom(WEATHER_VISIBILITY_TEMPLATES).format(
                value=currentVisibility,
                unit=weatherData.visibilityUnit
            ),

            pickRandom(WEATHER_PRECIPITATION_TEMPLATES).format(
                value=currentPrecipitation,
                chance=currentPrecipChance,
                unit=weatherData.precipitationUnit
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
