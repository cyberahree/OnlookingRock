from .styling import DEFAULT_FONT, BORDER_MARGIN

from PySide6.QtCore import QObject, QEvent, QTimer, QPoint
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget

from typing import Optional

class InterfaceComponent(QWidget):
    def __init__(
        self,
        sprite: QWidget,
        refreshRate: int = 10
    ):
        # top-level overlay
        super().__init__(None)

        self.sprite = sprite
        self.isInterfaceBuilt = False

        self.followTimer = QTimer(self)
        self.followTimer.setInterval(1000 // refreshRate)
        self.followTimer.timeout.connect(self._reposition)

        self.setFont(DEFAULT_FONT)
        self.anchorMargin = BORDER_MARGIN

    def build(self) -> None:
        # create widgets/layouts
        pass

    def ensureBuilt(self) -> None:
        if self.isInterfaceBuilt:
            return
        
        self.build()
        self.isInterfaceBuilt = True
    
    def updateAnchor(self) -> None:
        pass

    def open(self) -> None:
        self.ensureBuilt()
        self._reposition()
        self.show()
        self.raise_()
        self.activateWindow()
        self.followTimer.start()
    
    def closeEvent(self, event) -> None:
        self.followTimer.stop()
        super().closeEvent(event)
    
    def hideEvent(self, event) -> None:
        self.followTimer.stop()
        super().hideEvent(event)
    
    def _reposition(self) -> None:
        pass

    def clampToScreen(self, position: QPoint) -> QPoint:
        screenGeometry = QGuiApplication.primaryScreen().geometry()

        x = max(
            screenGeometry.left(),
            min(position.x(), screenGeometry.right() - self.width())
        )
        y = max(
            screenGeometry.top(),
            min(position.y(), screenGeometry.bottom() - self.height())
        )

        return QPoint(x, y)

class InterfaceManager(QObject):
    def __init__(self, sprite: QWidget):
        super().__init__()
        
        self.sprite = sprite
        self.components = {}

        self.sprite.installEventFilter(self)
    
    def registerComponent(
        self,
        name: str,
        component: InterfaceComponent
    ) -> None:
        self.components[name] = component
    
    def getComponent(self, name: str) -> Optional[InterfaceComponent]:
        return self.components.get(name, None)
    
    def open(self, name: str) -> None:
        component = self.getComponent(name)
        
        if not component:
            return
        
        component.open()
    
    def close(self, name: str) -> None:
        component = self.getComponent(name)
        
        if not component:
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
    
    def closeAll(self) -> None:
        for component in self.components.values():
            if not component.isVisible():
                continue

            component.close()

    def eventFilter(self, watched, event):
        # reposition components on sprite move/resize
        if (watched is self.sprite) and (event.type() in (QEvent.Move, QEvent.Resize)):
            for component in self.components.values():
                if not component.isVisible():
                    continue

                component._reposition()
        
        return super().eventFilter(watched, event)
