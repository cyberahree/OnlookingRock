from ..interfaces.windows.mediaview import MediaViewWindow

from ..system.sound import SoundManager
from ..config import ConfigController
from ..scene import SceneSystem

from ..sprite.speech import SpeechBubbleController

from .flags import InteractabilityFlags
from .discovery import discoverEvents
from .context import EventContext
from .base import BaseEvent

from PySide6.QtCore import QObject, QTimer, Signal

from typing import Callable, Dict, List, Optional
from dataclasses import dataclass

import logging
import random
import time

logger = logging.getLogger(__name__)

@dataclass
class EventRunState:
    eventId: str
    startedAtMs: int
    watchdogTimer: Optional[QTimer] = None

class EventManager(QObject):
    """
    scheduler for sprite random events

    :cvar eventTriggered: Emitted with the event ID and friendly name when an event fires.
    :vartype eventTriggered: PySide6.QtCore.Signal
    """
    eventTriggered = Signal(str, str)

    def __init__(
        self,
        sprite,
        config: ConfigController,
        flags: InteractabilityFlags,
        soundManager: SoundManager,
        sceneSystem: SceneSystem,
        speechBubble: SpeechBubbleController,
        mediaView: MediaViewWindow,
        canRun: Optional[Callable[[], bool]] = None
    ):
        """
        Initialise the event manager.

        :param sprite: The sprite instance this manager controls events for.
        :param config: Configuration controller providing event-related settings.
        :param flags: Interactability flags that influence whether events can run.
        :param soundManager: Manager responsible for playing sounds during events.
        :param sceneSystem: Scene system used to manage scene-related event behavior.
        :param speechBubble: Controller for displaying speech bubbles during events.
        :param canRun: Optional callback that returns True if events are allowed to run.
        """
        super().__init__(sprite)

        self.sprite = sprite
        self.config = config
        self.flags = flags
        self.soundManager = soundManager
        self.sceneSystem = sceneSystem
        self.speechBubble = speechBubble
        self.mediaView = mediaView

        self.eventsEnabled = True
        self.startupMinimumDelay = 15
        self.maxEventDuration = 120
        self.eventIntervalRange = {
            "min": 300,
            "max": 600
        }

        self.events: List[BaseEvent] = []
        self.canRun = canRun or (lambda: True)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._tick)

        self.isRunning = False
        self.activeEvent: Optional[EventRunState] = None
        self.lastEventRunMs: Dict[str, int] = {}

        self._loadFromConfig()
        self.config.onValueChanged.connect(self._onConfigChanged)

        self.ingestEventModules()

    # config handlers
    def _loadFromConfig(self):
        """
        Load event manager settings from configuration.
        """
        self.eventsEnabled = self.config.getValue("events.enabled")
        self.startupMinimumDelay = self.config.getValue("events.startupMinimumDelay")
        self.maxEventDuration = self.config.getValue("events.maxEventDuration")

        self.eventIntervalRange["min"] = self.config.getValue("events.eventIntervalRange.min")
        self.eventIntervalRange["max"] = self.config.getValue("events.eventIntervalRange.max")

    def _onConfigChanged(self, path: str, value: str):
        """
        Handle configuration changes for event-related settings.

        :param path: Configuration key path
        :type path: str
        :param value: New value for the configuration key
        :type value: str
        """
        if not path.startswith("events."):
            return

        path = path[len("events."):]

        if path == "enabled":
            self.eventsEnabled = value
        elif path == "startupMinimumDelay":
            self.startupMinimumDelay = value
        elif path == "maxEventDuration":
            self.maxEventDuration = value
        elif path == "eventIntervalRange.min":
            self.eventIntervalRange["min"] = value
        elif path == "eventIntervalRange.max":
            self.eventIntervalRange["max"] = value

    # module lifecycle
    def ingestEventModules(self):
        """
        discover and ingest event modules
        hahha one line function
        """
        self.events = discoverEvents()

    def start(self):
        """
        Start the event manager scheduler.
        """
        self.isRunning = True
        self.scheduleNext(
            isInitial=True
        )

    def stop(self):
        """
        Stop the event manager scheduler and finish any active event.
        """
        self.isRunning = False

        try:
            self._timer.stop()
        except Exception:
            pass

        self.finishActiveEvent(True)

    # external methods
    def getEvents(self) -> List[tuple[str, str]]:
        """
        Get the list of all registered events.

        :return: List of registered event ids and their friendly names
        :rtype: List[tuple[str, str]]
        """
        return [(e.id, e.name) for e in self.events]

    def getEvent(self, eventId: str) -> Optional[BaseEvent]:
        """
        Retrieve a specific event by its ID.

        :param eventId: The ID of the event to retrieve
        :type eventId: str
        :return: The event instance if found, None otherwise
        :rtype: Optional[BaseEvent]
        """
        return next((e for e in self.events if e.id == eventId), None)

    def getRemainingCooldown(self, eventId: str) -> Optional[int]:
        """
        Get the remaining cooldown time for a specific event.

        :param eventId: The ID of the event to check
        :type eventId: str
        :return: Remaining cooldown time in seconds, or None if not on cooldown
        :rtype: Optional[int]
        """
        now = self.nowMs()
        event = self.getEvent(eventId)

        if event is None:
            return None

        lastRan = self.lastEventRunMs.get(eventId)

        if lastRan is None:
            return None

        eventCooldownSeconds = event.cooldownSeconds

        if eventCooldownSeconds <= 0:
            return None

        delta = (now - lastRan) / 1000

        remaining = eventCooldownSeconds - delta

        if remaining <= 0:
            return None

        return int(remaining)

    def getFriendlyCooldownText(self, eventId: str) -> Optional[str]:
        """
        Get a user-friendly string representing the remaining cooldown time for an event.

        :param eventId: The ID of the event to check
        :type eventId: str
        :return: Friendly cooldown string (e.g., "2m 30s"), or None if not on cooldown
        :rtype: Optional[str]
        """
        remaining = self.getRemainingCooldown(eventId)

        if remaining is None:
            return None

        minutes = remaining // 60
        seconds = remaining % 60

        parts = []

        if minutes > 0:
            parts.append(f"{minutes}m")

        if seconds > 0 or minutes == 0:
            parts.append(f"{seconds}s")

        return " ".join(parts)

    def isEventEnabled(self, eventId: str) -> bool:
        """
        Check if a specific event is enabled.

        :param eventId: The ID of the event to check
        :type eventId: str
        :return: True if the event is enabled, False otherwise
        :rtype: bool
        """
        event = self.getEvent(eventId)

        if event is None:
            return False

        return event.isEnabled

    def triggerEvent(self, eventId: str) -> bool:
        """
        Manually trigger a specific event by its ID.

        :param eventId: The ID of the event to trigger
        :type eventId: str
        :return: True if the event was successfully triggered, False otherwise
        :rtype: bool
        """
        if not self.eventsEnabled:
            logger.debug("Cannot trigger event: events are disabled")
            return False
        
        if self.activeEvent is not None:
            logger.debug("Cannot trigger event: another event is already running")
            return False
        
        event = self.getEvent(eventId)

        if event is None:
            logger.debug(f"Cannot trigger event: event ID {eventId} not found")
            return False

        context = EventContext(
            sprite=self.sprite,
            flags=self.flags,
            soundManager=self.soundManager,
            sceneSystem=self.sceneSystem,
            speechBubble=self.speechBubble,
            mediaView=self.mediaView
        )

        try:
            if not event.canRun(context):
                logger.debug(f"Cannot trigger event: canRun gate failed for event ID {eventId}")
                return False
        except Exception as e:
            logger.error(f"Error checking canRun gate for event ID {eventId}: {e}")
            return False
        
        logger.debug(f"Manually triggering event: {event.id}")
        self.runEvent(event, context)

        return True

    def attemptEventTrigger(self) -> bool:
        """
        Manually trigger a random event, bypassing the normal scheduler.
        Useful for testing or user-initiated events.
        
        :return: True if an event was triggered, False otherwise
        :rtype: bool
        """
        if not self.eventsEnabled:
            logger.debug("Cannot trigger event: events are disabled")
            return False
        
        if self.activeEvent is not None:
            logger.debug("Cannot trigger event: another event is already running")
            return False
        
        try:
            if not self.canRun():
                logger.debug("Cannot trigger event: canRun gate failed")
                return False
        except Exception as e:
            logger.error(f"Error checking canRun gate: {e}")
            return False
        
        context = EventContext(
            sprite=self.sprite,
            flags=self.flags,
            soundManager=self.soundManager,
            sceneSystem=self.sceneSystem,
            speechBubble=self.speechBubble,
            mediaView=self.mediaView
        )
        
        candidateEvent = self.pickWeightedEvent(context)
        
        if candidateEvent is None:
            logger.debug("Cannot trigger event: no eligible events available")
            return False
        
        logger.debug(f"Manually triggering event: {candidateEvent.id}")
        self.runEvent(candidateEvent, context)
        return True

    # internal methods
    def nowMs(self) -> int:
        """
        Get the current time in milliseconds.

        :return: Current time in milliseconds since epoch
        :rtype: int
        """
        return int(time.time() * 1000)

    def scheduleNext(self, isInitial: bool = False) -> None:
        """
        Schedule the next event tick.

        :param isInitial: Whether this is the initial scheduling after start
        :type isInitial: bool
        """
        if not self.isRunning:
            return

        if not self.eventsEnabled:
            # poll occasionally so toggling on in config takes effect
            self._timer.start(10_000)
            return

        if isInitial:
            delayMs = int(self.startupMinimumDelay * 1000)
        else:
            delaySeconds = random.randint(
                self.eventIntervalRange["min"],
                self.eventIntervalRange["max"]
            )

            delayMs = int(delaySeconds * 1000)

        self._timer.start(max(250, delayMs))

    def pickWeightedEvent(self, context: EventContext) -> Optional[BaseEvent]:
        """
        Select a random event from eligible events based on their weights.

        Filters events by cooldown, enabled status, and canRun conditions,
        then randomly selects one based on their weight values.

        :param context: Event context for checking eligibility
        :type context: EventContext
        :return: Selected event or None if no eligible events
        :rtype: Optional[BaseEvent]
        """
        now = self.nowMs()

        runnable: List[BaseEvent] = []
        weights: List[float] = []

        for event in self.events:
            if not event.isEnabled:
                continue

            eventCooldownSeconds = event.cooldownSeconds
            lastRan = self.lastEventRunMs.get(event.id)

            logger.debug(f"Evaluating event {event.id}: cooldown={eventCooldownSeconds}, lastRan={lastRan}")

            if (eventCooldownSeconds > 0) and lastRan:
                delta = (now - lastRan) / 1000

                if delta < eventCooldownSeconds:
                    continue

            try:
                if not event.canRun(context):
                    continue
            except Exception as e:
                continue

            weight = event.weight

            if weight <= 0:
                continue

            runnable.append(event)
            weights.append(weight)

        logger.debug(f"Found {len(runnable)} runnable events.")

        if not runnable:
            return None
        
        try:
            chosenEvent = random.choices(runnable, weights=weights, k=1)[0]
            return chosenEvent
        except Exception as e:
            logger.error(f"Error picking weighted event: {e}")
            return random.choice(runnable)

    def runEvent(
        self,
        event: BaseEvent,
        context: EventContext
    ) -> None:
        """
        Execute an event with watchdog timer protection.

        :param event: The event to run
        :type event: BaseEvent
        :param context: Event context providing resources and state
        :type context: EventContext
        """
        startMs = self.nowMs()

        logger.debug(f"Starting event {event.id} ({event.name})")
        self.eventTriggered.emit(event.id, event.name)
        self.lastEventRunMs[event.id] = startMs

        maxDuration = event.maxDurationSeconds or self.maxEventDuration

        watchdogTimer = QTimer(self)
        watchdogTimer.setSingleShot(True)
        watchdogTimer.timeout.connect(lambda: self.finishActiveEvent(True))
        watchdogTimer.start(max(
            5000, (maxDuration * 1000)
        ))

        self.activeEvent = EventRunState(
            eventId=event.id,
            startedAtMs=startMs,
            watchdogTimer=watchdogTimer
        )

        isFinished = False

        def doneOnce():
            nonlocal isFinished

            if isFinished:
                return

            isFinished = True
            self.finishActiveEvent(False)
        
        try:
            event.run(
                context,
                doneOnce
            )
        except Exception as e:
            logger.error(f"Error running event {event.id}: {e}")
            doneOnce()

    def finishActiveEvent(self, force: bool) -> None:
        """
        Clean up and finish the currently active event.

        :param force: Whether the event is being forcibly terminated
        :type force: bool
        """
        if self.activeEvent is None:
            return

        # stop watchdog
        try:
            if self.activeEvent.watchdogTimer is not None:
                self.activeEvent.watchdogTimer.stop()
        except Exception:
            pass

        # release any lingering locks owned by this event id
        try:
            self.flags.clear_owner(self.activeEvent.eventId)
        except Exception:
            pass

        if force:
            logger.debug(f"Forcibly finished event: {self.activeEvent.eventId}")
        else:
            logger.debug(f"Finished event: {self.activeEvent.eventId}")

        self.activeEvent = None
        self.scheduleNext(isInitial=False)

    def _tick(self):
        """
        main event scheduler tick
        """
        # ensure timer is stopped before processing
        try:
            self._timer.stop()
        except Exception:
            pass
        
        if not self.isRunning:
            return
        
        if not self.eventsEnabled:
            self.scheduleNext(isInitial=False)
            return
    
        if self.activeEvent is not None:
            # shouldn't happen (single-shot scheduler), but keep it safe.
            self.scheduleNext(isInitial=False)
            return

        # global gates
        try:
            if not self.canRun():
                self.scheduleNext(isInitial=False)
                return
        except Exception as e:
            logger.error(f"Error checking canRun gate: {e}")
            self.scheduleNext(isInitial=False)
            return
        
        context = EventContext(
            sprite=self.sprite,
            flags=self.flags,
            soundManager=self.soundManager,
            sceneSystem=self.sceneSystem,
            speechBubble=self.speechBubble,
            mediaView=self.mediaView
        )

        candidateEvent = self.pickWeightedEvent(context)

        if candidateEvent is None:
            self.scheduleNext(isInitial=False)
            return
        
        self.runEvent(
            candidateEvent,
            context
        )
