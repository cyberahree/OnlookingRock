from ...sprite.templates import (
    WEATHER_TEMPERATURE_TEMPLATES,
    WEATHER_VISIBILITY_TEMPLATES,
    WEATHER_PRECIPITATION_TEMPLATES,
    pickRandom
)

from ...location import WeatherData
from ..context import EventContext
from ..base import BaseEvent

from PySide6.QtCore import QTimer

from datetime import datetime
from matplotlib import pyplot
from typing import Callable

import scipy.interpolate
import numpy
import time
import io

# graph functions
def _smoothSeries(
    seriesX: numpy.ndarray,
    seriesY: numpy.ndarray,
    factor: int = 10
) -> tuple[list[datetime], numpy.ndarray]:
    smoothX = numpy.linspace(
        seriesX[0],
        seriesX[-1],
        len(seriesX) * factor
    )

    interpolator = scipy.interpolate.PchipInterpolator(
        seriesX,
        seriesY
    )

    return [datetime.fromtimestamp(t) for t in smoothX], interpolator(smoothX)

def _chooseTemperatureColor(
    currentValue: float,
    nextValue: float,
    equilibriumTemperature: float
) -> str:
    if (currentValue <= equilibriumTemperature) and (nextValue <= equilibriumTemperature):
        return "#74b9ff"

    if (currentValue > equilibriumTemperature) and (nextValue > equilibriumTemperature):
        return "#ff6b6b"

    return "#ba92b5"

def _chooseVisibilityColor(
    visibility: float,
    isMetric: bool = True
) -> str:
    minBound = 1.5 if isMetric else 0.93
    midBound = 2.5 if isMetric else 1.55
    highBound = 3.5 if isMetric else 2.17
    maxBound = 5 if isMetric else 3.1

    # gradient bs
    if visibility < minBound:
        return "#ff0000"

    # AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    # linear interpolation time <3
    if visibility < midBound:
        normalised = (visibility - minBound) / (midBound - minBound)

        red = int(0xff + normalised * (0x00 - 0xff))
        green = int(0x00 + normalised * (0xff - 0x00))

        return f"#{red:02x}{green:02x}00"

    if visibility < highBound:
        return "#00ff00"

    if visibility < maxBound:
        normalised = (visibility - highBound) / (maxBound - highBound)

        red = int(0x00 + normalised * (0xec - 0x00))
        green = int(0xff + normalised * (0x00 - 0xff))
        blue = int(0x00 + normalised * (0xfc - 0x00))

        return f"#{red:02x}{green:02x}{blue:02x}"

    return "#ec00fc"

class WeatherEvent(BaseEvent):
    id = "weather"
    name = "Current Weather"

    weight = 0.35
    cooldownSeconds = 7200

    def canRun(self, context: EventContext) -> bool:
        if len(context.speech.queue) > 0 or context.speech.active:
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

        # generate graph
        graphBytes = self.buildGraph(weatherData)
        context.mediaView.showImagefromBytes(
            graphBytes,
            "Current Weather",
            openPanel=True
        )

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

    def buildGraph(
        self,
        weatherData: WeatherData
    ) -> bytes:
        """
        Builds a weather graph based on the provided weather data.
        
        :param weatherData: current weather data
        :type weatherData: WeatherData
        :return: buffer containing graph image
        :rtype: BytesIO
        """
        datetimes = [
            datetime.fromtimestamp(unix)
            for unix in weatherData.timestamps
        ]

        timestamps = numpy.array([
            datetimeObject.timestamp()
            for datetimeObject in datetimes
        ])

        temperature = numpy.array(weatherData.temperature)
        precipitation = numpy.array(weatherData.precipitation)
        precipChance = numpy.array(weatherData.precipitationChance)
        visibility = numpy.clip(
            numpy.array(weatherData.visibility),
            0, (5 if weatherData.isMetric else 3.1)
        )
        
        # generate smooth series
        timeSeriesSmooth, temperatureSmooth = _smoothSeries(
            numpy.array(timestamps),
            temperature
        )

        _, precipChanceSmooth = _smoothSeries(
            numpy.array(timestamps),
            precipChance
        )

        _, precipitationSmooth = _smoothSeries(
            numpy.array(timestamps),
            precipitation
        )

        timeSeriesSmoothVisibility, visibilitySmooth = _smoothSeries(
            numpy.array(timestamps),
            visibility
        )

        # figure setup
        figure, (temperatureAxis, precipitationAxis, visibilityAxis) = pyplot.subplots(
            3, 1,
            figsize=(12, 10),
            sharex=True
        )

        # -> type hints
        figure: pyplot.Figure
        temperatureAxis: pyplot.Axes
        precipitationAxis: pyplot.Axes
        visibilityAxis: pyplot.Axes

        # plot data

        # - temperature plot -
        equilibriumTemperature = 0 if weatherData.isMetric else 32

        # -> temperature line plot
        for index in range(len(temperatureSmooth) - 1):
            pointColor = _chooseTemperatureColor(
                temperatureSmooth[index],
                temperatureSmooth[index + 1],
                equilibriumTemperature
            )

            temperatureAxis.plot(
                [timeSeriesSmooth[index], timeSeriesSmooth[index + 1]],
                [temperatureSmooth[index], temperatureSmooth[index + 1]],
                color=pointColor,
                linewidth=2
            )

        # -> fill areas
        temperatureAxis.fill_between(
            timeSeriesSmooth,
            temperatureSmooth,
            where=(temperatureSmooth <= equilibriumTemperature),
            color="#74b9ff",
            interpolate=True,
            alpha=0.3
        )

        # -> scatter raw temperature points
        temperatureAxis.scatter(
            datetimes,
            temperature,
            color=[
                "#74b9ff" if t <= equilibriumTemperature else "#ff6b6b" for t in temperature
            ],
            alpha=0.6,
            zorder=3,
            s=20
        )

        # -> equilibrium line
        temperatureAxis.axhline(
            linestyle="--",
            color="gray",
            linewidth=0.8,
            alpha=0.5,
            y=0,
        )

        # -> labels, grid & legend
        temperatureAxis.set_title('Weather Forecast', fontweight='bold', fontsize=12)
        temperatureAxis.set_ylabel(f"Temperature (°{weatherData.temperatureUnit})")
        temperatureAxis.grid(True, alpha=0.3)

        legendElements = [
            pyplot.Line2D(
                [0], [0],
                color="#ff6b6b",
                linewidth=2,
                label=f"Temperature > {equilibriumTemperature}°{weatherData.temperatureUnit}"
            ),

            pyplot.Line2D(
                [0], [0],
                color="#74b9ff",
                linewidth=2,
                label=f"Temperature ≤ {equilibriumTemperature}°{weatherData.temperatureUnit}"
            )
        ]

        temperatureAxis.legend(
            handles=legendElements,
            loc="upper right"
        )

        # - precipitation value & chance plot -
        # -> primary axis for precipitation chance
        precipitationAxis.bar(
            datetimes,
            precipChance,
            label="Precipitation Chance (%)",
            color="#4ecdc4",
            alpha=0.7,
            width=0.03
        )

        # -> primary axis label & tick params
        precipitationAxis.set_ylabel(
            "Precipitation Chance (%)",
            color="#4ecdc4",
            #fontsize=11
        )

        precipitationAxis.tick_params(
            axis='y',
            labelcolor='#4ecdc4'
        )

        # -> twin axis for precipitation value
        twinAxis = precipitationAxis.twinx()

        # -> precipitation line plot
        twinAxis.plot(
            timeSeriesSmooth,
            precipitationSmooth,
            label=f"Precipitation ({weatherData.precipitationUnit})",
            color="#95afc0",
            linewidth=2
        )

        # -> scatter raw precipitation points
        precipitationMask = precipitation > 0
        twinAxis.scatter(
            [datetimes[i] for i in range(len(datetimes)) if precipitationMask[i]],
            precipitation[precipitationMask],
            color="#95afc0",
            alpha=0.5,
            zorder=3,
            s=20
        )

        # -> twin axis labels & limits
        twinAxis.set_ylabel(
            f"Precipitation ({weatherData.precipitationUnit})",
            color="#95afc0",
            #fontsize=11
        )

        # -> twin axis tick params
        twinAxis.tick_params(
            axis="y",
            labelcolor="#95afc0"
        )

        twinAxis.set_ylim(bottom=0)

        # -> grid & legends
        precipitationAxis.grid(True, alpha=0.3)
        precipitationAxis.legend(loc="upper left")
        twinAxis.legend(loc="upper right")

        # - visibility plot -
        # -> visibility line plot
        for index in range(len(visibilitySmooth) - 1):
            pointColor = _chooseVisibilityColor(
                visibilitySmooth[index],
                weatherData.isMetric
            )

            visibilityAxis.plot(
                [timeSeriesSmoothVisibility[index], timeSeriesSmoothVisibility[index + 1]],
                [visibilitySmooth[index], visibilitySmooth[index + 1]],
                color=pointColor,
                linewidth=2
            )
        
        # -> scatter raw visibility points
        maxVisibility = 5 if weatherData.isMetric else 3.1

        for time, visibilityRaw, visibilityCapped in zip(
            datetimes, visibility, numpy.clip(visibility, 0, maxVisibility)
        ):
            if visibilityRaw >= (maxVisibility - 1e-6):
                continue

            visibilityAxis.scatter(
                [time],
                [visibilityCapped],
                color=_chooseVisibilityColor(visibilityRaw, weatherData.isMetric),
                alpha=0.6,
                zorder=3,
                s=20
            )

        # -> limit
        visibilityAxis.set_ylim(bottom=0, top=maxVisibility + 0.5)

        # -> labels, grid & legend
        visibilityAxis.set_ylabel(
            f"Visibility ({weatherData.visibilityUnit})",
            #fontsize=11
        )

        visibilityAxis.set_xlabel("Time") #, fontsize=11
        visibilityAxis.grid(True, alpha=0.3)

        poorVisibility = 2 if weatherData.isMetric else 1.24
        decentVisibility = 4 if weatherData.isMetric else 2.48
        greatVisibility = 5 if weatherData.isMetric else 3.1

        legendElementsVis = [
            pyplot.Line2D(
                [0], [0],
                color="#ff0000",
                linewidth=2,
                label=f"Visibility < {(poorVisibility)}{weatherData.visibilityUnit}"
            ),

            pyplot.Line2D(
                [0], [0],
                color="#00ff00",
                linewidth=2,
                label=f"Visibility {(poorVisibility)}-{(decentVisibility)}{weatherData.visibilityUnit}"
            ),

            pyplot.Line2D(
                [0], [0],
                color="#ec00fc",
                linewidth=2,
                label=f"Visibility >= {(greatVisibility)}{weatherData.visibilityUnit} (capped at {(maxVisibility)}{weatherData.visibilityUnit})"
            )
        ]

        visibilityAxis.legend(
            handles=legendElementsVis,
            loc="upper right"
        )

        # current time marker
        nowDateTime = datetime.now()

        for ax in [temperatureAxis, precipitationAxis, visibilityAxis]:
            ax.axvline(
                nowDateTime,
                color='#7f8c8d',
                linestyle='--',
                linewidth=1.2,
                alpha=0.85
            )

        # time formatting
        visibilityAxis.xaxis.set_major_formatter(
            pyplot.matplotlib.dates.DateFormatter('%H:%M')
        )

        visibilityAxis.xaxis.set_major_locator(
            pyplot.matplotlib.dates.HourLocator(interval=2)
        )

        pyplot.gcf().autofmt_xdate()
        pyplot.tight_layout()

        # export to a buffer
        buffer = io.BytesIO()
        figure.savefig(
            buffer,
            format='png',
            dpi=100,
            bbox_inches='tight'
        )

        buffer.seek(0)
        graphBytes = buffer.getvalue()

        buffer.close()
        pyplot.close(figure)

        return graphBytes

EVENTS = [
    WeatherEvent()
]
