from .config import ConfigController

from dataclasses import dataclass
from typing import Optional

import requests
import random
import time

IP_API = "http://ip-api.com/json/"
OPEN_METEO = "https://api.open-meteo.com/v1/forecast"

IP_LOCATION_CUTOFF_SECONDS = (60 * 60 * 24) # 24 hours
CACHE_CUTOFF_WEATHER_SECONDS = (60 * 60) # 1 hour

TIME_DESCRIPTIONS = {
    (0, 0): ["midnight", "the witching hour"],
    (1, 3): ["late night", "the dead of night", "the small hours"],
    (4, 5): ["dawn", "early morning", "sunrise", "daybreak"],
    (6, 11): ["morning", "mid-morning"],
    (12, 12): ["noon", "midday"],
    (13, 16): ["afternoon", "mid-afternoon"],
    (17, 18): ["evening", "dusk", "twilight"],
    (19, 19): ["sunset", "sundown"],
    (20, 23): ["night", "nighttime", "evening"]
}

UNITS = [
    # temperature, precipitation, visibility
    ["C", "millimetres", "kilometres"], # metric
    ["F", "inches", "miles"]  # imperial
]

@dataclass
class Location:
    city: str
    country: str

    lat_lon: Optional[
        tuple[float, float]
    ]

@dataclass
class WeatherData:
    timestamps: list[int] # unix timestamps
    temperature: list[float] # c
    precipitation: list[float] # mm
    precipitationChance: list[float] # %
    visibility: list[float] # km

    isMetric: bool = True
    temperatureUnit: str = "C"
    precipitationUnit: str = "mm"
    visibilityUnit: str = "km"

temperatureAsFarenheit: float = lambda temperatureC: (temperatureC * 9/5) + 32
precipitationAsInches: float = lambda precipitationMm: precipitationMm / 25.4
visibilityAsMiles: float = lambda visibilityKm: visibilityKm / 1.60934

class LocationServices:
    """
    manages application permissions and related functionality
    """
    def __init__(
        self,
        configController: ConfigController
    ):
        """
        initialise the services controller with required dependencies
        """

        self.config = configController

    def getFriendlyLocalTime(self) -> str:
        """
        gets a friendly representation of the current local time

        :return: the friendly local time string
        :rtype: str
        """

        localTime = time.localtime()
        hour = localTime.tm_hour

        for hourRange, descriptions in TIME_DESCRIPTIONS.items():
            if hourRange[0] <= hour <= hourRange[1]:
                return random.choice(descriptions)
            
        return "today"

    def locationPermissionAllowed(self) -> bool:
        """
        checks if location fetching is allowed by user configuration

        :return: whether location fetching is allowed
        :rtype: bool
        """

        return (self.config.getValue("location.allowedGeoIpFetch") == True)

    def getLocation(self) -> Optional[Location]:
        """
        gets an inaccurate location using ip geolocation

        :return: the inaccurate location or None if unavailable
        :rtype: Optional[Location]
        """
        if not self.locationPermissionAllowed():
            return None
        
        lastFetchTimestamp = self.config.getValue("location.ipStats.lastUpdated")

        currentTimestamp = time.time()

        if (
            lastFetchTimestamp is not None
            and (currentTimestamp - lastFetchTimestamp) < IP_LOCATION_CUTOFF_SECONDS
        ):
            cachedCity = self.config.getValue("location.ipStats.city")
            cachedCountry = self.config.getValue("location.ipStats.country")
            cachedLat = self.config.getValue("location.ipStats.lat")
            cachedLon = self.config.getValue("location.ipStats.lon")

            hasCoordinates = (cachedLat is not None) and (cachedLon is not None)

            return Location(
                city=cachedCity,
                country=cachedCountry,
                lat_lon=(cachedLat, cachedLon) if hasCoordinates else None
            )

        ipResponse = requests.get(IP_API, timeout=10)

        if not ipResponse.ok:
            return None
        
        ipData = ipResponse.json()

        latitude = ipData.get("lat")
        longitude = ipData.get("lon")

        hasCoordinates = (latitude is not None) and (longitude is not None)

        locationObject = Location(
            city=ipData.get("city", "Unknown"),
            country=ipData.get("country", "Unknown"),

            lat_lon=(latitude, longitude) if hasCoordinates else None
        )

        # update cached location info
        self.config.bulkSetValues(
            {
                "lastUpdated": currentTimestamp,
                "city": locationObject.city,
                "country": locationObject.country,
                "lat": latitude,
                "lon": longitude
            },
            parentPath="location.ipStats"
        )

        return locationObject

    def getWeatherData(self, location: Location = None) -> Optional[WeatherData]:
        """
        gets weather data for the given location if permission is granted
        AND if weather data has not been recently fetched

        cached weather data is stored in configuration, and will be returned
        if it is still valid

        :param location: the location to get weather data for
        :type location: Location

        :return: the weather data or None if unavailable
        :rtype: Optional[WeatherData]
        """

        if location is None:
            location = self.getLocation()
        
        cachedWeatherStats = self.config.getValue("location.weatherStats") or {}

        # cache object
        lastCacheTimestamp = cachedWeatherStats.get("lastUpdated", 0)
        currentTimestamp = time.time()

        # units system
        preferMetric = (self.config.getValue("location.preferMetric") == True)
        unitSet = UNITS[0] if preferMetric else UNITS[1]

        # 1) default to cached values (even if stale or empty)
        timestamps = cachedWeatherStats.get("timestamps", [])
        temperature = cachedWeatherStats.get("temperature", [])
        precipitation = cachedWeatherStats.get("precipitation", [])
        precipitationChance=cachedWeatherStats.get("precipitationChance", [])
        visibility = cachedWeatherStats.get("visibility", [])

        # 2) revalidate only if cache is stale, or doesnt exist
        cacheDoesntExist = (lastCacheTimestamp == 0 or len(timestamps) == 0)
        cacheIsStale =  (currentTimestamp - lastCacheTimestamp) >= CACHE_CUTOFF_WEATHER_SECONDS

        if cacheDoesntExist or cacheIsStale:
            # 2.1) collect new data
            weatherResponse = requests.get(
                OPEN_METEO,
                params={
                    "latitude": location.lat_lon[0],
                    "longitude": location.lat_lon[1],
                    "hourly": "temperature_2m,precipitation,precipitation_probability,visibility",
                    "timezone": "auto",
                    "forecast_days": 1
                }
            )

            # 2.2) failed to get weather data
            if not weatherResponse.ok:
                return None

            weatherData = weatherResponse.json().get("hourly")

            if weatherData is None:
                return None
            
            # 2.3) convert timestamps to unix
            unixTimestamps = []

            for isoTimestamp in weatherData.get("time", []):
                structTime = time.strptime(isoTimestamp, "%Y-%m-%dT%H:%M")
                unixTimestamps.append(int(time.mktime(structTime)))

            # 2.4) convert metres to kilometres
            visibilityKm = []
            for visMetres in weatherData.get("visibility", []):
                visibilityKm.append(visMetres / 1000.0)

            timestamps: list[int] = unixTimestamps
            temperature: list[float] = weatherData.get("temperature_2m", [])
            precipitation: list[float] = weatherData.get("precipitation", [])
            precipitationChance: list[float] = weatherData.get("precipitation_probability", [])
            visibility: list[float] = visibilityKm

            # 2.5) update cached weather stats
            self.config.bulkSetValues(
                {
                    "lastUpdated": currentTimestamp,
                    "timestamps": timestamps,
                    "temperature": temperature,
                    "precipitation": precipitation,
                    "precipitationChance": precipitationChance,
                    "visibility": visibility
                },
                parentPath="location.weatherStats"
            )

        # 3) convert to imperial if needed
        if not preferMetric:
            convertedTemperature = []
            convertedPrecipitation = []
            convertedVisibility = []

            minLen = min(len(temperature), len(precipitation), len(visibility))

            for i in range(minLen):
                tempC = temperature[i]
                precipMm = precipitation[i]
                visKm = visibility[i]

                convertedTemperature.append(
                    temperatureAsFarenheit(tempC)
                )

                convertedPrecipitation.append(
                    precipitationAsInches(precipMm)
                )

                convertedVisibility.append(
                    visibilityAsMiles(visKm)
                )

            temperature = convertedTemperature
            precipitation = convertedPrecipitation
            visibility = convertedVisibility

        # 4) return assembled weather data
        return WeatherData(
            timestamps=timestamps,
            temperature=temperature,
            precipitation=precipitation,
            precipitationChance=precipitationChance,
            visibility=visibility,

            isMetric=preferMetric,
            temperatureUnit=unitSet[0],
            precipitationUnit=unitSet[1],
            visibilityUnit=unitSet[2]
        )
