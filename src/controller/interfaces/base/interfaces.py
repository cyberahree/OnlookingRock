from .styling import DEFAULT_FONT, BORDER_MARGIN, ANIMATION_OPACITY_DURATION

from ..mixin import FadeableMixin

from PySide6.QtCore import (
    QObject, QEvent, QTimer, QPoint, Qt,
    QPropertyAnimation, QEasingCurve, Signal
)

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QGuiApplication

from typing import Optional

class InterfaceComponent(QWidget, FadeableMixin):
    fadeFinished = Signal(float)

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
        self.followTimer.setInterval(max(1, 1000 // refreshRate))
        self.followTimer.timeout.connect(self._reposition)

        self.setFont(DEFAULT_FONT)
        self.anchorMargin = BORDER_MARGIN

        self.moveAnimation = QPropertyAnimation(self, b"pos")
        self.moveAnimation.setDuration(1000 // refreshRate)
        self.moveAnimation.setEasingCurve(QEasingCurve.OutCubic)

        self.enableMoveAnimation = True
        self.moveAnimationMinDuration = 80
        self.moveAnimationMaxDuration = 300

        self.initFadeable(
            durationMs=ANIMATION_OPACITY_DURATION,
            startOpacity=1.0,
            easing=QEasingCurve.OutCubic,
        )

        self.fadeOnOpen = True
        self.fadeOnClose = True
        self._fadeClosePending = False

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

    def onFadeFinished(self, endOpacity: float) -> None:
        if endOpacity <= 0.001:
            self._fadeClosePending = False

    def open(self) -> None:
        self.ensureBuilt()
        self._reposition()

        if self.fadeOnOpen:
            self.setOpacity(0.0)

        self.show()
        self.raise_()
        
        if self.sprite:
            try:
                self.sprite.raise_()
            except Exception:
                pass

        # dont steal focus unless we want to
        if (self.focusPolicy() != Qt.NoFocus) and (not self.testAttribute(Qt.WA_ShowWithoutActivating)):
            self.activateWindow()

        if self.fadeOnOpen:
            self.fadeIn()

        self.followTimer.start()
    
    def close(self) -> bool:
        # if fading out, do NOT call *.close()
        # hint: it hides immediately
        if self.fadeOnClose and self.isVisible():
            self._fadeClosePending = True
            self.followTimer.stop()
            self.fadeOut()
            return True

        return super().close()
    
    def closeEvent(self, event) -> None:
        self.followTimer.stop()
        
        if hasattr(self, "fadeAnimation"):
            self.fadeAnimation.stop()
        
        if hasattr(self, "moveAnimation"):
            self.moveAnimation.stop()

        super().closeEvent(event)
    
    def hideEvent(self, event) -> None:
        self.followTimer.stop()
        
        if hasattr(self, "fadeAnimation"):
            self.fadeAnimation.stop()
        
        if hasattr(self, "moveAnimation"):
            self.moveAnimation.stop()

        super().hideEvent(event)
    
    def _reposition(self) -> None:
        pass

    def animateTo(self, target: QPoint) -> None:
        if not self.isVisible():
            if hasattr(self, "moveAnimation"):
                self.moveAnimation.stop()

            self.move(target)
            return

        if not self.enableMoveAnimation:
            self.move(target)
            return

        if self.moveAnimation.state() == QPropertyAnimation.Running:
            self.moveAnimation.stop()

        distance = (self.pos() - target).manhattanLength()
        duration = min(self.moveAnimationMaxDuration, max(self.moveAnimationMinDuration, distance))

        self.moveAnimation.setDuration(duration)
        self.moveAnimation.setStartValue(self.pos())
        self.moveAnimation.setEndValue(target)
        self.moveAnimation.start()

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
