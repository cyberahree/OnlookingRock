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

from typing import Callable, Optional

class _FollowConnection(QObject):
    """
    internal class managing connection of a callback to a timer for continuous tracking
    """

    def __init__(
        self,
        timer: QTimer,
        callback: Callable[[], None], parent: Optional[QObject] = None
    ):
        """
        Initialise follow connection.

        :param timer: QTimer to connect callback to
        :type timer: QTimer
        :param callback: Callback function to execute on timer timeout
        :param parent: Parent QObject, defaults to None
        :type parent: Optional[QObject]
        """
        super().__init__(parent)
        self._timer = timer
        self._callback = callback
        self._active = False

    def start(self) -> None:
        """
        Connect callback to timer and start executing on timeout.
        """
        if self._active:
            return

        try:
            self._timer.timeout.connect(self._callback)
        except Exception:
            pass

        self._active = True

    def stop(self) -> None:
        """
        Disconnect callback from timer to stop executing.
        """
        if not self._active:
            return

        try:
            self._timer.timeout.disconnect(self._callback)
        except Exception:
            pass

        self._active = False

class InterfaceComponent(QWidget, FadeableMixin):
    """
    base class for interface components with positioning, animation, and fade support
    """

    fadeFinished = Signal(float)

    def __init__(
        self,
        sprite: QWidget,
        clock: Optional[TimingClock] = None,
    ):
        """
        Initialise interface component

        :param sprite: The sprite widget this component is associated with
        :type sprite: QWidget
        :param clock: Optional timing clock for refresh rate, defaults to None
        :type clock: Optional[TimingClock]
        """
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
        """
        Build the interface component structure. Override in subclasses.
        """
        pass

    def ensureBuilt(self) -> None:
        """
        Ensure the component is built before use.
        """
        if self.isInterfaceBuilt:
            return

        self.build()
        self.isInterfaceBuilt = True

    def updateAnchor(self) -> None:
        """
        Update anchor positioning for the component. Override in subclasses.
        """
        pass

    def onFadeFinished(self, endOpacity: float) -> None:
        """
        Handle fade animation completion.

        :param endOpacity: Final opacity value
        :type endOpacity: float
        """
        if endOpacity <= 0.001:
            self._fadeClosePending = False

    def open(self) -> None:
        """
        Open and display the component with animation.
        """
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
        """
        Close the component with animation if fade is enabled.

        :return: True if fade animation was triggered, False otherwise
        :rtype: bool
        """
        if self.fadeOnClose and self.isVisible():
            self._fadeClosePending = True
            self.followTimer.stop()
            self.fadeOut()
            return True

        return super().close()

    def closeEvent(self, event) -> None:
        """
        Handle close event by stopping animations and timers.

        :param event: The close event
        """
        self.followTimer.stop()

        if hasattr(self, "fadeAnimation"):
            self.fadeAnimation.stop()

        if hasattr(self, "moveAnimation"):
            self.moveAnimation.stop()

        super().closeEvent(event)

    def hideEvent(self, event) -> None:
        """
        Handle hide event by stopping animations and timers.

        :param event: The hide event
        """
        self.followTimer.stop()

        if hasattr(self, "fadeAnimation"):
            self.fadeAnimation.stop()

        if hasattr(self, "moveAnimation"):
            self.moveAnimation.stop()

        super().hideEvent(event)

    def _reposition(self) -> None:
        """
        Reposition the component. Override in subclasses to implement custom positioning.
        """
        pass

    def animateTo(self, target: QPoint) -> None:
        """
        Animate the component to a target position with smooth easing.

        :param target: Target position for the component
        :type target: QPoint
        """
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
        """
        Clamp a position to stay within the primary screen bounds.

        :param position: Position to clamp
        :type position: QPoint
        :return: Clamped position within screen bounds
        :rtype: QPoint
        """
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
