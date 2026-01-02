from .positioning import bestCandidate
from .styling import BORDER_MARGIN

from PySide6.QtCore import QPoint, QRect, QSize
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget

from typing import Callable, Iterable, Optional, Sequence

class PrimaryScreenAnchorMixin:
    """
    mixin providing anchor positioning relative to the primary screen
    """

    def primaryAvailableGeometry(self) -> QRect:
        """
        Get the available geometry of the primary screen.

        :return: The available geometry of the primary screen, or an empty rect if unavailable
        :rtype: QRect
        """
        screen = QGuiApplication.primaryScreen()
        return screen.availableGeometry() if screen else QRect(0, 0, 0, 0)

    def anchorBottomRight(self, *, margin: int = BORDER_MARGIN) -> QPoint:
        """
        Get the bottom-right anchor point on the primary screen.

        :param margin: Margin from screen edges, defaults to BORDER_MARGIN
        :type margin: int
        :return: The bottom-right anchor point
        :rtype: QPoint
        """
        screen = self.primaryAvailableGeometry()
        size = self.size()

        x = screen.left() + screen.width() - size.width() - margin
        y = screen.top() + screen.height() - size.height() - margin

        return QPoint(x, y)

class SpriteAnchorMixin:
    """
    mixin providing anchor positioning relative to a sprite widget
    """

    def spriteFrameGeometry(self) -> QRect:
        """
        Get the frame geometry of the sprite widget.

        :return: The frame geometry of the sprite, or an empty rect if sprite is unavailable
        :rtype: QRect
        """
        sprite = getattr(self, "sprite", None)

        if sprite is None:
            return QRect(0, 0, 0, 0)

        try:
            topLeft = sprite.mapToGlobal(QPoint(0, 0))
            return QRect(topLeft, sprite.size())
        except Exception:
            return QRect(0, 0, 0, 0)

    def spriteAvailableGeometry(self) -> QRect:
        """
        Get the available geometry of the screen containing the sprite.

        :return: The available geometry of the sprite's screen, or an empty rect if unavailable
        :rtype: QRect
        """
        sprite = getattr(self, "sprite", None)

        if sprite is None:
            return QRect(0, 0, 0, 0)

        try:
            screen = sprite.screen()
            return screen.availableGeometry() if screen else QRect(0, 0, 0, 0)
        except Exception:
            return QRect(0, 0, 0, 0)

    def getOccluderWidgets(
        self,
        provider: Optional[Callable[[], Iterable[QWidget]]] = None,
    ) -> list[QWidget]:
        """
        Get visible occluder widgets from the provider function.

        :param provider: Optional callable that provides iterable of widgets, defaults to None
        :type provider: Optional[Callable[[], Iterable[QWidget]]]
        :return: List of visible occluder widgets
        :rtype: list[QWidget]
        """
        provider = provider or getattr(self, "occludersProvider", None) or (lambda: [])

        try:
            widgets = list(provider() or [])
        except Exception:
            widgets = []

        visibleWidgets: list[QWidget] = []

        for widget in widgets:
            if widget is None:
                continue

            # this COULD raise exceptions in some cases
            # we catch them and skip those widgets
            try:
                if not widget.isVisible():
                    continue
            except Exception:
                continue

            visibleWidgets.append(widget)

        return visibleWidgets

    def getOccluderBounds(
        self,
        provider: Optional[Callable[[], Iterable[QWidget]]] = None,
    ) -> list[QRect]:
        """
        Get the frame geometry bounds of occluder widgets.

        :param provider: Optional callable that provides iterable of widgets, defaults to None
        :type provider: Optional[Callable[[], Iterable[QWidget]]]
        :return: List of occluder widget frame geometries
        :rtype: list[QRect]
        """
        rects: list[QRect] = []

        for widget in self.getOccluderWidgets(provider):
            try:
                rects.append(widget.frameGeometry())
            except Exception:
                continue

        return rects

    def restackOccluders(
        self,
        provider: Optional[Callable[[], Iterable[QWidget]]] = None,
    ) -> None:
        """
        Restack occluder widgets to keep them on top of the sprite.

        :param provider: Optional callable that provides iterable of widgets, defaults to None
        :type provider: Optional[Callable[[], Iterable[QWidget]]]
        """
        if not getattr(self, "keepOccludersOnTop", False):
            return

        for widget in self.getOccluderWidgets(provider):
            try:
                widget.raise_()
            except Exception:
                pass

    def _spriteSidePoints(
        self,
        *,
        size: QSize,
        margin: int,
        yAlign: str,
        preferredSide: str,
        xOffset: int = 0,
        yOffset: int = 0,
    ) -> tuple[QPoint, QPoint]:
        spriteBounds = self.spriteFrameGeometry()

        if yAlign == "top":
            baseY = spriteBounds.top()
        elif yAlign == "bottom":
            baseY = spriteBounds.bottom() - size.height()
        else:
            baseY = spriteBounds.center().y() - (size.height() // 2)

        rightX = spriteBounds.right() + margin
        leftX = spriteBounds.left() - size.width() - margin

        rightPoint = QPoint(rightX + xOffset, baseY + yOffset)
        leftPoint = QPoint(leftX + xOffset, baseY + yOffset)

        if preferredSide == "left":
            return (leftPoint, rightPoint)

        return (rightPoint, leftPoint)

    def anchorNextToSprite(
        self,
        *,
        yAlign: str = "center",
        preferredSide: str = "right",
        margin: int = 0,
        xOffset: int = 0,
        yOffset: int = 0,
        occluders: Optional[Sequence[QRect]] = None,
        occludersProvider: Optional[Callable[[], Iterable[QWidget]]] = None,
    ) -> QPoint:
        screen = self.spriteAvailableGeometry()
        size = self.size()

        preferred, alternate = self._spriteSidePoints(
            size=size,
            margin=int(margin),
            yAlign=str(yAlign),
            preferredSide=str(preferredSide),
            xOffset=int(xOffset),
            yOffset=int(yOffset),
        )

        if occluders is None:
            occluders = self.getOccluderBounds(occludersProvider)

        # include the sprite itself as an occluder so widgets flip
        # to the opposite side when the sprite is covering them
        spriteBounds = self.spriteFrameGeometry()

        if not spriteBounds.isNull():
            occluders = list(occluders) + [spriteBounds]

        return bestCandidate(
            preferred,
            alternate,
            size,
            screen,
            list(occluders),
            int(margin),
        )

    def inwardHorizontalDirection(
        self,
        targetTopLeft: QPoint,
        *,
        size: Optional[QSize] = None,
    ) -> str:
        spriteRect = self.spriteFrameGeometry()
        size = size or self.size()

        widgetCenterX = targetTopLeft.x() + (size.width() // 2)
        spriteCenterX = spriteRect.center().x()

        return "left" if spriteCenterX < widgetCenterX else "right"
