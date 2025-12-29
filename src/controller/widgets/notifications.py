from ..interfaces.components.notification import ToastStackComponent, PopupAction

from typing import Callable, Optional, Sequence
from dataclasses import dataclass

@dataclass
class MessageHandle:
    dismiss: Callable[[], None]

class NotificationController:
    def __init__(
        self,
        sprite,
        refreshRate: int = 10,
        widthPx: int = 360,
        maxVisible: int = 5,
    ) -> None:
        self.component = ToastStackComponent(
            sprite=sprite,
            refreshRate=refreshRate,
            widthPx=widthPx,
            maxVisible=maxVisible,
        )

    def post(
        self,
        kind: str,
        title: str,
        message: str,
        actions: Sequence[PopupAction] = (),
        timeoutMs: Optional[int] = None,
    ) -> MessageHandle:
        item = self.component.post(
            kind=kind,
            title=title,
            message=message,
            actions=actions,
            timeoutMs=timeoutMs,
        )

        return MessageHandle(dismiss=item.dismiss)

    def info(
        self,
        title: str,
        message: str,
        timeoutMs: int = 4500
    ) -> MessageHandle:
        return self.post("info", title, message, timeoutMs=timeoutMs)

    def error(
        self,
        title: str,
        message: str,
        timeoutMs: int = 0
    ) -> MessageHandle:
        # default is no auto-dismiss for errors
        return self.post("error", title, message, timeoutMs=timeoutMs)

    def action(
        self,
        title: str,
        message: str,
        actions: Sequence[PopupAction],
        timeoutMs: int = 0,
    ) -> MessageHandle:
        return self.post("action", title, message, actions=actions, timeoutMs=timeoutMs)

    def clear(self) -> None:
        self.component.clear()
