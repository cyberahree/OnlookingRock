from .config import ConfigController

from dataclasses import dataclass
from typing import Optional

import requests
import random
import time

IP_API = "https://ip-api.com/json/"
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
    visibility: list[float] # metres

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

    def getLocation(self) -> Optional[Location]:
        """
        gets an inaccurate location using ip geolocation

        :return: the inaccurate location or None if unavailable
        :rtype: Optional[Location]
        """
        allowedGeoIpFetch = self.config.getValue("location.allowedGeoIpFetch")

        if not allowedGeoIpFetch:
            return None
        
        lastFetchTimestamp = self.config.getValue("location.geoIpFetchTimestamp")

        currentTimestamp = time.time()

        if (currentTimestamp - lastFetchTimestamp) < IP_LOCATION_CUTOFF_SECONDS:
            cachedCity = self.config.getValue("location.city")
            cachedCountry = self.config.getValue("location.country")
            cachedLat = self.config.getValue("location.latitude")
            cachedLon = self.config.getValue("location.longitude")

            hasCoordinates = (cachedLat is not None) and (cachedLon is not None)

            return Location(
                city=cachedCity,
                country=cachedCountry,
                lat_lon=(cachedLat, cachedLon) if hasCoordinates else None
            )

        ipResponse = requests.get(IP_API)

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
                "geoIpFetchTimestamp": currentTimestamp,
                "city": locationObject.city,
                "country": locationObject.country,
                "latitude": latitude,
                "longitude": longitude
            },
            parentPath="location"
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
        
        if location is None or location.lat_lon is None:
            return None

        cachedWeatherStats = self.config.getValue("location.weatherStats")
        lastCacheTimestamp = cachedWeatherStats.get("lastFetchTimestamp", 0)

        currentTimestamp = time.time()

        if (currentTimestamp - lastCacheTimestamp) < CACHE_CUTOFF_WEATHER_SECONDS:
            return WeatherData(
                timestamps=cachedWeatherStats.get("timestamps", []),
                temperature=cachedWeatherStats.get("temperature", []),
                precipitation=cachedWeatherStats.get("precipitation", []),
                precipitationChance=cachedWeatherStats.get("precipitationChance", []),
                visibility=cachedWeatherStats.get("visibility", [])
            )
        
        weatherResponse = requests.get(
            OPEN_METEO,
            params={
                "latitude": location.lat_lon[0],
                "longitude": location.lat_lon[1],
                "hourly": "temperature_2m,precipitation,precipitationChance,visibility",
                "timezone": "auto",
                "forecast_days": 1
            }
        )

        if not weatherResponse.ok:
            return None
        
        weatherData = weatherResponse.json().get("hourly")

        if weatherData is None:
            return None
        
        # convert timestamps to unix
        unixTimestamps = []

        for isoTimestamp in weatherData.get("time", []):
            structTime = time.strptime(isoTimestamp, "%Y-%m-%dT%H:%M")
            unixTimestamps.append(int(time.mktime(structTime)))
        
        weatherData["time"] = unixTimestamps

        weatherStats = WeatherData(
            timestamps=weatherData.get("time", []),
            temperature=weatherData.get("temperature_2m", []),
            precipitation=weatherData.get("precipitation", []),
            precipitationChance=weatherData.get("precipitationChance", []),
            visibility=weatherData.get("visibility", [])
        )

        # update cached weather stats
        self.config.bulkSetValues(
            {
                "lastFetchTimestamp": currentTimestamp,
                "timestamps": weatherStats.timestamps,
                "temperature": weatherStats.temperature,
                "precipitation": weatherStats.precipitation,
                "precipitationChance": weatherStats.precipitationChance,
                "visibility": weatherStats.visibility
            },
            parentPath="location.weatherStats"
        )

        return weatherStats
