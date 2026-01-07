from .removeDecoration import RemoveDecorationEvent
from .motivationalSpeech import MotivationEvent
from .randomThought import RandomThoughtEvent
from .uselessFact import UselessFactEvent
from .currentWeather import WeatherEvent
from .currentTime import TimeEvent
from .jokeSpeech import JokeEvent
from .quickNap import NapEvent

EVENTS = [
    RemoveDecorationEvent,
    MotivationEvent,
    RandomThoughtEvent,
    UselessFactEvent,
    WeatherEvent,
    TimeEvent,
    JokeEvent,
    NapEvent,
]
