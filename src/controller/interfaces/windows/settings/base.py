from ...base.modality import SpriteNudgeController
from ...base import InterfaceComponent
from ...base.styling import PADDING

from ...base.lookskit import (
    BodyLabel,
    CloseButton,
    ContentRow,
    Divider,
    HeadingLabel,
    SurfaceFrame,
    applyRockStyle,
)

from ....config.settingsstore import SettingsStore
from ....system.timings import TimingClock

from PySide6.QtWidgets import QApplication, QComboBox, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, QEvent, QPoint, QRect
from PySide6.QtGui import QGuiApplication

from typing import Optional

class SettingsModalComponent(InterfaceComponent):
    def __init__(
        self,
        sprite: QWidget,
        settings: SettingsStore,
        clock: Optional[TimingClock] = None,
    ):
        super().__init__(sprite, clock)

        self.settings = settings

        self.setWindowFlags(
            Qt.Tool |
            Qt.Dialog |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )

        self.setWindowModality(Qt.NonModal)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.StrongFocus)

        QApplication.instance().installEventFilter(self)

        self.setFixedWidth(384)
        self.spriteNudger = SpriteNudgeController(sprite)

    def build(self) -> None:
        self.setObjectName("settingsModal")

        root = SurfaceFrame(self, padding=PADDING)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(root)

        layout = root.contentLayout

        headerRow = ContentRow()
        self.titleLabel = HeadingLabel("Settings")

        headerRow.addWidget(self.titleLabel)
        headerRow.addStretch(1)

        self.closeButton = CloseButton(self, self.close)
        headerRow.addWidget(self.closeButton)

        layout.addLayout(headerRow)
        layout.addWidget(Divider())

        profileRow = ContentRow()
        profileRow.addWidget(BodyLabel("Profile:"))

        self.profileCombo = QComboBox(self)
        self.profileCombo.setMinimumWidth(160)
        self.profileCombo.currentIndexChanged.connect(self._onProfileChanged)

        profileRow.addWidget(self.profileCombo, 1)
        layout.addLayout(profileRow)

        applyRockStyle(self)

    def open(self) -> None:
        self.ensureBuilt()
        self._refreshProfiles()

        self.adjustSize()
        self._reposition()

        if self.fadeOnOpen:
            self.setOpacity(0.0)

        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.ActiveWindowFocusReason)
        self.spriteNudger.nudgeIfOverlapping(self)

        if self.fadeOnOpen:
            self.fadeIn()

        self.followTimer.stop()

    def closeEvent(self, event) -> None:
        self.spriteNudger.restore()
        super().closeEvent(event)

    def _refreshProfiles(self) -> None:
        current = self.settings.activeProfile()
        profiles = self.settings.listProfiles()

        self.profileCombo.blockSignals(True)
        self.profileCombo.clear()
        self.profileCombo.addItems(profiles)

        index = self.profileCombo.findText(current)
        self.profileCombo.setCurrentIndex(index if index >= 0 else 0)
        self.profileCombo.blockSignals(False)

    def _onProfileChanged(self, _index: int) -> None:
        if not hasattr(self, "profileCombo"):
            return

        profile = self.profileCombo.currentText().strip()
        if not profile:
            return

        self.settings.switchProfile(profile)

    def _availableGeometry(self) -> QRect:
        screen = None

        try:
            screen = self.sprite.screen() if self.sprite else None
        except Exception:
            screen = None

        if screen is None:
            screen = QGuiApplication.primaryScreen()

        if screen is None:
            return QRect(0, 0, 800, 600)

        return screen.availableGeometry()

    def _reposition(self) -> None:
        screenBounds = self._availableGeometry()

        x = screenBounds.left() + (screenBounds.width() - self.width()) // 2
        y = screenBounds.top() + (screenBounds.height() - self.height()) // 2

        x = max(screenBounds.left(), min(x, screenBounds.left() + screenBounds.width() - self.width()))
        y = max(screenBounds.top(), min(y, screenBounds.top() + screenBounds.height() - self.height()))

        self.move(QPoint(x, y))

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self.close()
            event.accept()
            return

        super().keyPressEvent(event)

    def eventFilter(self, watched, event) -> bool:
        if (not self.isVisible()) or (event.type() != QEvent.MouseButtonPress):
            return False

        globalPos = event.globalPos()
        widget = QApplication.widgetAt(globalPos)

        if widget is None:
            self.close()
            return False

        if (widget is self) or self.isAncestorOf(widget):
            return False

        if (widget is self.sprite) or (self.sprite and self.sprite.isAncestorOf(widget)):
            return False

        self.close()
        return False

