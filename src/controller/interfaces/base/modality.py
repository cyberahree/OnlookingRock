from .styling import BORDER_MARGIN

from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QPoint, QRect
from PySide6.QtWidgets import QWidget

from typing import Optional

class SpriteNudgeController:
    """
    controller for nudging a sprite widget to avoid overlapping with modal windows
    """

    def __init__(self, sprite: QWidget, margin: int = BORDER_MARGIN) -> None:
        """
        Initialise sprite nudge controller.

        :param sprite: The sprite widget to control
        :type sprite: QWidget
        :param margin: Margin from screen edges, defaults to BORDER_MARGIN
        :type margin: int
        """
        self.sprite = sprite
        self.margin = margin

        self.spriteNudged: bool = False

    def nudgeIfOverlapping(self, window: QWidget) -> bool:
        """
        Nudge sprite if it overlaps with a modal window.

        :param window: The modal window to check overlap with
        :type window: QWidget
        :return: True if sprite was nudged, False otherwise
        :rtype: bool
        """
        if not self.sprite or not window:
            return False

        if not self.sprite.isVisible() or not window.isVisible():
            return False

        screenBounds = self._availableGeometry()

        modalRect = window.frameGeometry()
        spriteRect = self.sprite.frameGeometry()

        if not modalRect.intersects(spriteRect):
            return False

        sw, sh = spriteRect.width(), spriteRect.height()

        left = screenBounds.left()
        top = screenBounds.top()
        right_excl = screenBounds.left() + screenBounds.width()
        bottom_excl = screenBounds.top() + screenBounds.height()

        leftX = modalRect.left() - sw - self.margin
        rightX = modalRect.right() + 1 + self.margin

        candidates: list[QPoint] = []

        if leftX >= left:
            candidates.append(QPoint(leftX, spriteRect.top()))

        if rightX + sw <= right_excl:
            candidates.append(QPoint(rightX, spriteRect.top()))

        if candidates:
            origX = spriteRect.left()
            target = min(candidates, key=lambda p: abs(p.x() - origX))
            newX, newY = target.x(), target.y()
        else:
            newX = left if modalRect.center().x() >= screenBounds.center().x() else (right_excl - sw)
            newY = spriteRect.top()

        newY = max(top, min(newY, bottom_excl - sh))

        self.sprite.move(int(newX), int(newY))
        self.spriteNudged = True
        return True

    def _availableGeometry(self) -> QRect:
        """
        Get the available geometry of the sprite's screen.

        :return: The available screen geometry for positioning
        :rtype: QRect
        """
        screen = None

        try:
            screen = self.sprite.screen() if self.sprite else None
        except Exception:
            screen = None

        if screen is None:
            screen = QGuiApplication.primaryScreen()

        return screen.availableGeometry() if screen else QRect(0, 0, 800, 600)
