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
    "it's currently {}°C outside",
    "the temperature right now is {}°C",
    "it's a {} degree Celsius day",
    "outside, it's about {}°C",
    "the thermometer reads {}°C at the moment",
]

WEATHER_VISIBILITY_TEMPLATES = [
    "the visibility is currently {} metres",
    "you can see up to {} metres right now",
    "the visibility distance is around {} metres",
    "it's about {} metres visibility at the moment",
    "right now, the visibility is approximately {} metres",
]

WEATHER_PRECIPITATION_TEMPLATES = [
    # formatting argunments:
    # amount = millimeters
    # chance = percentage
    "theres's a {chance}% chance of precipitation with {amount}mm expected",
    "expect around {amount}mm of precipitation, with a {chance}% chance",
    "the forecast shows a {chance}% chance of precipitation, with {amount}mm likely",
    "precipitation is expected at {amount}mm, with a {chance}% chance",
    "currently, there's a {chance}% chance of precipitation, with {amount}mm anticipated",
]
