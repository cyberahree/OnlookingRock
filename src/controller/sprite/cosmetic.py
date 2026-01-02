from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

class HatOverlayWindow(QWidget):
    """
    manages a transparent overlay window for displaying cosmetic hats on the sprite
    """

    def __init__(self, sprite: QWidget):
        """
        initialise the hat overlay window as a transparent overlay on the sprite.
        
        :param sprite: The sprite widget to overlay
        :type sprite: QWidget
        """

        super().__init__(
            sprite,
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.WindowTransparentForInput |
            Qt.Tool
        )

        self.spriteWindow = sprite

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
        """
        set the pixmap to display as the hat and reposition the window.
        
        :param pixmap: The hat image pixmap to display
        :type pixmap: QPixmap
        """

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
        """
        reposition the hat overlay to centre on the sprite.
        """

        if self._pixmap.isNull():
            return

        # centre-to-centre alignment in global coords
        spriteCentre = self.spriteWindow.mapToGlobal(self.spriteWindow.rect().center())

        newX = int(spriteCentre.x() - (self._pixmap.width() / 2))
        newY = int(spriteCentre.y() - (self._pixmap.height() / 2))
        self.move(newX, newY)

    def shutdown(self) -> None:
        """
        shut down the overlay window and clean up resources.
        """

        try:
            self.hide()
        finally:
            self.close()
