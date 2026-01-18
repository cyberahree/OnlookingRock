from .modules.__registry__ import EVENTS
from .base import BaseEvent

import importlib
import pkgutil
import logging

logger = logging.getLogger(__name__)

def collectEventsFromModule(
    module: importlib.ModuleType
) -> list[BaseEvent]:
    """
    Collect event instances from a module's EVENTS list.

    :param module: The module to collect events from
    :type module: importlib.ModuleType
    :return: List of event instances found in the module
    :rtype: list[BaseEvent]
    """
    moduleEvents = []

    if not hasattr(module, "EVENTS"):
        return moduleEvents
    
    for event in module.EVENTS:
        if not isinstance(event, BaseEvent):
            logger.warning(
                f"Event {event} in module {module.__name__} is not an instance of BaseEvent"
            )

            continue

        moduleEvents.append(event)

    return moduleEvents

def discoverEvents() -> list[BaseEvent]:
    """
    Discover and load all events from the modules package.

    Searches through all modules in the events.modules package,
    imports them, and collects their EVENTS lists.

    :return: List of all discovered event instances
    :rtype: list[BaseEvent]
    """
    allEvents = []

    # if this errors, we have bigger problems to deal with
    modules = importlib.import_module(".modules", package=__package__)

    for module in pkgutil.iter_modules(modules.__path__, modules.__name__ + "."):
        if module.name.endswith("__example__") or module.name.endswith("__registry__"):
            continue

        try:
            importedModule = importlib.import_module(module.name)

            events = collectEventsFromModule(
                importedModule
            )

            allEvents.extend(events)
        except Exception as e:
            logger.error(f"Failed to load events from module {module.name}: {e}")

    logger.debug(f"Discovered {len(allEvents)} events from modules")
    logger.debug(f"Events: {[event.id for event in allEvents]}")

    if len(allEvents) == 0:
        allEvents = EVENTS

    return allEvents
