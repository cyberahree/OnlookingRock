from ..styling import PADDING

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtCore import Qt, QSize

from typing import Optional

def makeIconSquare(
    source: QPixmap,
    size: QSize = QSize(32, 32),
    margin: int = 2
) -> QIcon:
    if source.isNull():
        return QIcon()

    width, height = size.width(), size.height()
    canvas = QPixmap(width, height)
    canvas.fill(Qt.transparent)

    availableWidth = max(1, width - margin * 2)
    availableHeight = max(1, height - margin * 2)

    scaled = source.scaled(
        availableWidth,
        availableHeight,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation
    )

    x = (width - scaled.width()) // 2
    y = (height - scaled.height()) // 2

    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    painter.drawPixmap(x, y, scaled)
    painter.end()

    return QIcon(canvas)

class ContentColumn(QVBoxLayout):
    def __init__(self, parent: Optional[QWidget] = None, *, spacing: Optional[int] = 0):
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)

        self.setSpacing(
            PADDING // 2 if spacing is None else int(max(0, spacing))
        )

class ContentRow(QHBoxLayout):
    def __init__(self, parent: Optional[QWidget] = None, *, spacing: Optional[int] = 0):
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)

        self.setSpacing(
            PADDING // 2 if spacing is None else int(max(0, spacing))
        )
