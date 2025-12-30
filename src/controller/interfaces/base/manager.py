from .component import InterfaceComponent

from PySide6.QtCore import QObject, QEvent
from PySide6.QtWidgets import QWidget

from typing import Optional

class InterfaceManager(QObject):
    def __init__(self, sprite: QWidget):
        super().__init__()

        self.sprite = sprite
        self.components: dict[str, InterfaceComponent] = {}

        self.sprite.installEventFilter(self)

    def registerComponent(
            self,
            name: str,
            component: InterfaceComponent,
            ignoreOpenCheck: bool = False
        ) -> None:
        component.ignoreOpenCheck = ignoreOpenCheck
        self.components[name] = component

    def getComponent(self, name: str) -> Optional[InterfaceComponent]:
        return self.components.get(name, None)

    def open(self, name: str) -> None:
        component = self.getComponent(name)

        if not component:
            return
        
        if component.isVisible():
            return

        component.open()

    def close(self, name: str) -> None:
        component = self.getComponent(name)

        if not component:
            return
        
        if not component.isVisible():
            return

        component.close()

    def toggle(self, name: str) -> None:
        component = self.getComponent(name)

        if not component:
            return

        if component.isVisible():
            component.close()
        else:
            component.open()

    def isAnyOpen(self) -> bool:
        for component in self.components.values():
            if not component.isVisible():
                continue

            if component.ignoreOpenCheck:
                continue
            
            return True

        return False

    def closeAll(self) -> None:
        for component in self.components.values():
            if not component.isVisible():
                continue

            component.close()

    def eventFilter(self, watched, event):
        if (watched is self.sprite) and (event.type() in (QEvent.Move, QEvent.Resize)):
            for component in self.components.values():
                if not component.isVisible():
                    continue

                component._reposition()

        return super().eventFilter(watched, event)
