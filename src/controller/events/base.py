from .context import EventContext

from typing import Callable

class BaseEvent:
    """
    base class for all sprite events.
    
    :cvar id: unique identifier for the event
    :vartype id: str
    :cvar weight: relative weight for event selection; higher values increase selection probability
    :vartype weight: float
    :cvar isEnabled: whether the event is currently enabled and can be selected
    :vartype isEnabled: bool
    :cvar cooldownSeconds: minimum seconds to wait before this event can run again
    :vartype cooldownSeconds: int
    :cvar maxDurationSeconds: maximum duration in seconds for the event; None means unlimited
    :vartype maxDurationSeconds: int | None
    """

    id: str = ""
    name: str = ""

    isEnabled: bool = True
    weight: float = 1.0
    cooldownSeconds: int = 0

    maxDurationSeconds: int | None = None

    def canRun(self, context: EventContext) -> bool:
        """
        Determine if the event can run in the given context.

        :param context: The context in which to evaluate if the event can run.
        :return: True if the event can run, False otherwise.
        """
        return True

    def run(
        self,
        context: EventContext,
        onFinished: Callable[[], None]
    ) -> None:
        """
        Execute the event logic.

        :param context: The context in which the event is run.
        :type context: EventContext
        :param onFinished: Callback to be invoked when the event is finished.
        :type onFinished: Callable[[], None]
        """
        raise NotImplementedError
