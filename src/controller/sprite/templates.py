from typing import Any

import random

def pickRandom(Any: list[Any]) -> Any:
    """
    picks a random element from a list

    :param Any: the list to pick from
    :return: a random element from the list
    :rtype: Any
    """

    return random.choice(Any)

TIME_TEMPLATE = [
    # friendly time descriptions are passed through
    "hows {} treating you?",
    "its {} already, huh?",
    "{} vibes, am i right?",
    "{} edition",
    "yoo, {} check!!1!!",
    "feeling {} energy",
    "ah, {}. we meet again.",
    "caught you in {}",
    "im awake; unfortunately its {}",
    "my internal tick tock clock says its '{}'",
    "SITREP: {}",
    "greetings from {}",
    "reporting live at {}",
    "currently experiencing {}",
    "i crawled out of my pebble cave at {}"
]

USER_FEELING_TEMPLATE = [
    # name is passed through
    "how are you feeling {}?",
    "how are you doing today?",
    "whats up?",
    "how's it going?",
    "how have you been feeling lately?",
    "everything good on your end?",
    "you doing alright {}?",
    "how's life treating you {}?",
    "how's your day been so far?",
    "how've you been {}?",
    "how's everything going?",
    "i hope you're doing well :D",
    "how's things {}?",
]

CUTE_FACES = [
    "^^",
    ":3",
    ":D",
    "^w^",
    "UwU",
    "OwO",
    ">w<",
    "^_^",
    "n_n",
    "^-^",
    "x3",
    "QwQ",
    "UwU",
]

WEATHER_TEMPERATURE_TEMPLATES = [
    # formatting arguments:
    # value = temperature value
    # unit = C/F
    "it's currently {value}°{unit} outside",
    "the temperature right now is {value}°{unit}",
    "it's a {value}°{unit} day",
    "outside, it's about {value}°{unit}",
    "the thermometer reads {value}°{unit} at the moment",
]

WEATHER_VISIBILITY_TEMPLATES = [
    # formatting arguments:
    # value = visibility distance
    # unit = kilometres/miles
    "the visibility is currently {value} {unit}",
    "you can see up to {value} {unit} right now",
    "the visibility distance is around {value} {unit}",
    "it's about {value} {unit} visibility at the moment",
    "right now, the visibility is approximately {value} {unit}",
]

WEATHER_PRECIPITATION_TEMPLATES = [
    # formatting argunments:
    # value = millimeters
    # chance = percentage
    # unit = millimetres/inches
    "theres's a {chance}% chance of precipitation with {value} {unit} expected",
    "expect around {value} {unit} of precipitation, with a {chance}% chance",
    "the forecast shows a {chance}% chance of precipitation, with {value} {unit} likely",
    "precipitation is expected at {value} {unit}, with a {chance}% chance",
    "currently, there's a {chance}% chance of precipitation, with {value} {unit} anticipated",
]
