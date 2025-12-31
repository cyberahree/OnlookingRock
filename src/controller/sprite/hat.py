from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

class HatOverlayWindow(QWidget):
    def __init__(self, spriteWindow: QWidget):
        super().__init__(
            spriteWindow,
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.WindowTransparentForInput |
            Qt.Tool
        )

        self.spriteWindow = spriteWindow

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_AlwaysStackOnTop, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.NoFocus)

        self.label = QLabel(self)
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.label.setAttribute(Qt.WA_TranslucentBackground)
        self.label.setAlignment(Qt.AlignCenter)
        self.raise_()

        self._pixmap = QPixmap()

    def setHatPixmap(self, pixmap: QPixmap) -> None:
        self._pixmap = pixmap or QPixmap()

        if self._pixmap.isNull():
            self.hide()
            return

        self.label.setPixmap(self._pixmap)
        self.resize(self._pixmap.size())
        self.label.resize(self._pixmap.size())
        self.reposition()

        if self.isHidden():
            self.show()

    def reposition(self) -> None:
        if self._pixmap.isNull():
            return

        # centre-to-centre alignment in global coords
        spriteCentre = self.spriteWindow.mapToGlobal(self.spriteWindow.rect().center())

        newX = int(spriteCentre.x() - (self._pixmap.width() / 2))
        newY = int(spriteCentre.y() - (self._pixmap.height() / 2))
        self.move(newX, newY)

    def shutdown(self) -> None:
        try:
            self.hide()
        finally:
            self.close()
