from .positioning import bestCandidate
from .styling import BORDER_MARGIN

from PySide6.QtCore import QPoint, QRect, QSize
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget

from typing import Callable, Iterable, Optional, Sequence

class PrimaryScreenAnchorMixin:
    def primaryAvailableGeometry(self) -> QRect:
        screen = QGuiApplication.primaryScreen()
        return screen.availableGeometry() if screen else QRect(0, 0, 0, 0)

    def anchorBottomRight(self, *, margin: int = BORDER_MARGIN) -> QPoint:
        screen = self.primaryAvailableGeometry()
        size = self.size()

        x = screen.left() + screen.width() - size.width() - margin
        y = screen.top() + screen.height() - size.height() - margin

        return QPoint(x, y)

class SpriteAnchorMixin:
    def spriteFrameGeometry(self) -> QRect:
        sprite = getattr(self, "sprite", None)

        if sprite is None:
            return QRect(0, 0, 0, 0)

        try:
            return sprite.frameGeometry()
        except Exception:
            return QRect(0, 0, 0, 0)

    def spriteAvailableGeometry(self) -> QRect:
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
