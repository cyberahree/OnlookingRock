from .base import BaseEvent

import importlib
import pkgutil
import logging

logger = logging.getLogger(__name__)

def collectEventsFromModule(
    module: importlib.ModuleType
) -> list[BaseEvent]:
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
    allEvents = []

    # if this errors, we have bigger problems to deal with
    modules = importlib.import_module(".modules", package=__package__)

    for module in pkgutil.iter_modules(modules.__path__, modules.__name__ + "."):
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

    return allEvents
