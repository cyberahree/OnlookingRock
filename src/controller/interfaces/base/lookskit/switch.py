from ..styling import TEXT_COLOR, ENABLED_COLOR
from .primitives import _RockWidgetMixin

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QPen

from typing import Optional, Callable

class ToggleSwitch(QWidget, _RockWidgetMixin):
    """
    a simple toggle switch widget
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        checked: bool = False,
        onChanged: Optional[Callable[[bool], None]] = None,
    ):
        super().__init__(parent)
        self._setRole("switch", "default")
        
        self._checked = checked
        self._onChanged = onChanged
        
        # colors
        self._handleColor = QColor(255, 255, 255, 230)
        self._handleColorHover = QColor(255, 255, 255, 255)
        
        self._isHovered = False
        
        self.setFixedSize(44, 24)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool) -> None:
        if self._checked != checked:
            self._checked = checked
            self.update()

    def toggle(self) -> None:
        self.setChecked(not self._checked)
        if self._onChanged is not None:
            self._onChanged(self._checked)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Calculate dimensions
        width = self.width()
        height = self.height()
        track_radius = height / 2
        handle_radius = (height - 6) / 2
        
        # Draw track
        trackBounds = QRectF(0, 0, width, height)
        trackColor = ENABLED_COLOR if self._checked else TEXT_COLOR
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(trackColor)
        painter.drawRoundedRect(trackBounds, track_radius, track_radius)
        
        # Draw handle
        handlePosition = 1.0 if self._checked else 0.0
        handleX = 3 + (width - 6 - handle_radius * 2) * handlePosition
        handleY = height / 2
        
        handleColor = self._handleColorHover if self._isHovered else self._handleColor
        painter.setBrush(handleColor)
        
        # Add subtle shadow/border to handle
        painter.setPen(QPen(QColor(0, 0, 0, 30), 1))
        painter.drawEllipse(
            QRectF(
                handleX,
                handleY - handle_radius,
                handle_radius * 2,
                handle_radius * 2
            )
        )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.toggle()
    
        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:
        self._isHovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._isHovered = False
        self.update()
        super().leaveEvent(event)
