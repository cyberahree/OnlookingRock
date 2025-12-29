from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QPoint, QRect

class PrimaryScreenAnchorMixin:
    def primaryAvailableGeometry(self) -> QRect:
        screen = QGuiApplication.primaryScreen()
        return screen.availableGeometry() if screen else QRect(0, 0, 0, 0)

    def anchorBottomRight(self, *, margin: int = 0) -> QPoint:
        screen = self.primaryAvailableGeometry()
        size = self.size()

        x = screen.left() + screen.width() - size.width() - margin
        y = screen.top() + screen.height() - size.height() - margin

        return QPoint(x, y)
