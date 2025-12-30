from ...system.timings import TimingClock

from .styling import DEFAULT_FONT, BORDER_MARGIN, ANIMATION_OPACITY_DURATION
from .animation import FadeableMixin

from PySide6.QtCore import (
    QObject,
    QPoint,
    Qt,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
    Signal,
)

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QGuiApplication

from typing import Optional

class _FollowConnection(QObject):
    def __init__(
        self,
        timer: QTimer,
        callback, parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self._timer = timer
        self._callback = callback
        self._active = False

    def start(self) -> None:
        if self._active:
            return

        try:
            self._timer.timeout.connect(self._callback)
        except Exception:
            pass

        self._active = True

    def stop(self) -> None:
        if not self._active:
            return

        try:
            self._timer.timeout.disconnect(self._callback)
        except Exception:
            pass

        self._active = False

class InterfaceComponent(QWidget, FadeableMixin):
    fadeFinished = Signal(float)

    def __init__(
        self,
        sprite: QWidget,
        clock: Optional[TimingClock] = None,
    ):
        super().__init__(None)

        self.sprite = sprite
        self.isInterfaceBuilt = False

        self.clock = clock or TimingClock(15, self)
        self.followTimer = _FollowConnection(self.clock.timer, self._reposition)

        self.setFont(DEFAULT_FONT)
        self.anchorMargin = BORDER_MARGIN

        self.moveAnimation = QPropertyAnimation(self, b"pos")
        self.moveAnimation.setDuration(self.clock.timer.interval())
        self.moveAnimation.setEasingCurve(QEasingCurve.OutCubic)

        # link to refreshRate updates
        try:
            self.clock.refreshRateChanged.connect(
                lambda interval: self.moveAnimation.setDuration(interval)
            )
        except Exception:
            pass

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

        if (self.focusPolicy() != Qt.NoFocus) and (not self.testAttribute(Qt.WA_ShowWithoutActivating)):
            self.activateWindow()

        if self.fadeOnOpen:
            self.fadeIn()

        self.followTimer.start()

    def close(self) -> bool:
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
            min(position.x(), screenGeometry.right() - self.width()),
        )
        y = max(
            screenGeometry.top(),
            min(position.y(), screenGeometry.bottom() - self.height()),
        )

        return QPoint(x, y)
