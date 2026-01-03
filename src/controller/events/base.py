from typing import Callable

class BaseEvent:
    """
    base class for all sprite events
    """

    id: str = ""
    weight: float = 1.0

    isEnabled: bool = True
    cooldownSeconds: int = 0

    maxDurationSeconds: int | None = None

    def canRun(self, context) -> bool:
        """
        Determine if the event can run in the given context.

        :param context: The context in which to evaluate if the event can run.
        :return: True if the event can run, False otherwise.
        """
        return True

    def run(
        self,
        context,
        onFinished: Callable[[], None]
    ) -> None:
        """
        Execute the event logic.

        :param context: The context in which the event is run.
        :param onFinished: Callback to be invoked when the event is finished.
        """
        raise NotImplementedError
