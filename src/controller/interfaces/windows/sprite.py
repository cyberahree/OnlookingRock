from ..base.anchor import SpriteAnchorMixin
from ..base import InterfaceComponent

from ..base.lookskit import (
    BodyLabel,
    CloseButton,
    Divider,
    SubheadingLabel,
    SurfaceFrame,
    applyRockStyle,
    buildTextInputRow,
    buildDropdownRow,
    buildScaleSliderRow,
    buildSpinboxRow,
    buildSwitchRow,
)

from ..base.styling import (
    BACKGROUND_COLOR,
    BORDER_MARGIN,
    DEFAULT_FONT,
    PADDING,
    TEXT_COLOR,
    asRGB,
)

from ...config import ConfigController

from PySide6.QtCore import Qt, QEvent, QTimer
from PySide6.QtGui import QColor

from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QVBoxLayout,
    QWidget
)

from typing import Callable, Iterable, Optional

def clamp(value: float, minVal: float = 0.0, maxVal: float = 1.0) -> float:
    return max(minVal, min(maxVal, float(value)))

class SpriteWindowComponent(InterfaceComponent, SpriteAnchorMixin):
    """
    sprite settings window with controls for nickname, appearance, and refresh rates.
    
    Provides sliders and inputs for configuring sprite display and timing parameters with debounced config persistence.
    """

    def __init__(
        self,
        sprite: QWidget,
        clock,
        config: ConfigController,
        occludersProvider: Optional[Callable[[], Iterable[QWidget]]] = (lambda: []),
    ):
        """
        initialise the sprite settings window component.
        
        :param sprite: the sprite widget to anchor to
        :type sprite: QWidget
        :param clock: the timing clock instance
        :param config: the configuration controller
        :type config: ConfigController
        :param occludersProvider: callable returning occluders to avoid
        :type occludersProvider: Optional[Callable[[], Iterable[QWidget]]]
        """

        super().__init__(sprite, clock)

        self.config = config
        self.occludersProvider = occludersProvider

        self.setWindowFlags(
            Qt.Tool |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )

        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFont(DEFAULT_FONT)

        self.setOpacity(0.0)

        # debounce config writes
        self._saveTimer = QTimer(self)
        self._saveTimer.setSingleShot(True)
        self._saveTimer.setInterval(450)
        self._saveTimer.timeout.connect(self._saveConfigNow)

    def build(self) -> None:
        """
        construct the settings ui with input controls and sliders.
        """

        self.setObjectName("spriteWindow")
        self.setFixedWidth(320)

        self.rootFrame = SurfaceFrame(self, padding=PADDING)
        outerLayout = QVBoxLayout(self)
        outerLayout.setContentsMargins(0, 0, 0, 0)
        outerLayout.addWidget(self.rootFrame)
        rootLayout = self.rootFrame.layout()

        # header
        headerWidget = QWidget()
        headerLayout = QHBoxLayout(headerWidget)
        headerLayout.setContentsMargins(0, 0, 0, 0)
        headerLayout.setSpacing(PADDING // 2)

        self.titleLabel = SubheadingLabel("Sprite Settings")
        self.titleLabel.setObjectName("spriteTitle")
        headerLayout.addWidget(self.titleLabel, 1)

        self.closeButton = CloseButton(onClick=self.close)
        headerLayout.addWidget(self.closeButton, 0, Qt.AlignRight)

        rootLayout.addWidget(headerWidget)
        rootLayout.addWidget(Divider())

        # User Nickname
        nickRow, self._nickEdit = buildTextInputRow(
            "User Nickname",
            onChanged=lambda text: self._applyKeyValue("userNick", text),
        )
        rootLayout.addWidget(nickRow)
        rootLayout.addWidget(Divider())

        # Hat selection
        hatRow, self.hatDropdown = buildDropdownRow(
            "Hat",
            items=self.sprite.allHats,
            on_changed=lambda text: self._applyKeyValue("hat", text),
        )
        rootLayout.addWidget(hatRow)
        rootLayout.addWidget(Divider())

        # Scale slider
        scaleRow, self._scaleSlider, self._scaleLabel = buildScaleSliderRow(
            "Scale",
            minScale=0.25,
            maxScale=2.0,
            on_changed=None,
            onReleased=lambda scale: self._applyKeyValue("scale", scale),
        )
        rootLayout.addWidget(scaleRow)
        rootLayout.addWidget(Divider())

        # Refresh Rates
        rootLayout.addWidget(BodyLabel("Refresh Rates", selectable=False))
        primaryRow, self._primaryLoopSpinBox = buildSpinboxRow(
            "Primary Loop",
            minValue=1,
            maxValue=240,
            step=1,
            suffix=" Hz",
            on_changed=lambda v: self._applyKeyValue("primaryLoop", v),
        )
        rootLayout.addWidget(primaryRow)
        secondaryRow, self._secondaryLoopSpinBox = buildSpinboxRow(
            "Secondary Loop",
            minValue=1,
            maxValue=240,
            step=1,
            suffix=" Hz",
            on_changed=lambda v: self._applyKeyValue("secondaryLoop", v),
        )
        rootLayout.addWidget(secondaryRow)
        rootLayout.addWidget(Divider())

        # permissions
        rootLayout.addWidget(BodyLabel("Permissions", selectable=False))
        geoIpRow, self._geoIpSwitch, self._geoIpStateLabel = buildSwitchRow(
            "GeoIP fetching",
            on_changed=lambda v: self._applyKeyValue("allowedGeoIpFetch", v),
        )
        rootLayout.addWidget(geoIpRow)

        # style
        onHoverBackground = QColor(BACKGROUND_COLOR).darker(106)
        applyRockStyle(
            self,
            extraQss=f"""
            QLabel#spriteTitle {{
                color: {asRGB(TEXT_COLOR)};
                padding: 0px;
            }}

            QSlider::groove:horizontal {{
                height: {PADDING // 2}px;
                background: rgba(0, 0, 0, 25);
                border-radius: 3px;
            }}

            QSlider::sub-page:horizontal {{
                background: rgba({TEXT_COLOR.red()}, {TEXT_COLOR.green()}, {TEXT_COLOR.blue()}, 120);
                border-radius: 3px;
            }}

            QSlider::handle:horizontal {{
                width: 14px;
                margin: -5px 0px;
                border-radius: 7px;
                background: rgba(255, 255, 255, 200);
                border: 1px solid rgba(0, 0, 0, 40);
            }}

            QSlider::handle:horizontal:hover {{
                background: {asRGB(onHoverBackground)};
            }}
            """,
        )

        self._syncFromConfig()

    def _applyKeyValue(self, key: str, value) -> None:
        """
        apply a setting change and trigger config save.
        
        :param key: the configuration key to update
        :type key: str
        :param value: the new value to set
        """

        if key == "userNick":
            self.config.setValue("sprite.userNick", value)
        elif key == "hat":
            self.config.setValue("sprite.hat", value)
        elif key == "scale":
            scale = clamp(value, 0.25, 2.0)
            self.config.setValue("sprite.scale", scale)
            self._scaleLabel.setText(f"{scale:.2f}x")
        elif key == "primaryLoop":
            self.config.setValue("sprite.refreshRates.primaryLoop", value)
        elif key == "secondaryLoop":
            self.config.setValue("sprite.refreshRates.secondaryLoop", value)
        elif key == "allowedGeoIpFetch":
            self.config.setValue("location.allowedGeoIpFetch", value)

        self._scheduleSave()

    def _scheduleSave(self) -> None:
        """
        schedule a debounced config save operation.
        """

        # restart debounce timer
        self._saveTimer.stop()
        self._saveTimer.start()

    def _saveConfigNow(self) -> None:
        """
        immediately save configuration to disk.
        """

        try:
            self.config.saveConfig()
        except Exception:
            pass

    def _syncFromConfig(self) -> None:
        """
        synchronise ui controls with current configuration values.
        """

        # user nickname
        try:
            userNick = str(self.config.getValue("sprite.userNick"))
        except Exception:
            userNick = "<USERNAME>"

        self._nickEdit.blockSignals(True)
        self._nickEdit.setText(userNick)
        self._nickEdit.blockSignals(False)

        # hat
        try:
            hat = str(self.config.getValue("sprite.hat"))
        except Exception:
            hat = "None"

        self.hatDropdown.blockSignals(True)
        index = self.hatDropdown.findText(hat)

        if index >= 0:
            self.hatDropdown.setCurrentIndex(index)

        self.hatDropdown.blockSignals(False)

        # scale
        try:
            scale = clamp(self.config.getValue("sprite.scale"), 0.25, 2.0)
        except Exception:
            scale = 0.75

        self._scaleSlider.blockSignals(True)
        self._scaleSlider.setValue(int(round(scale * 100)))
        self._scaleSlider.blockSignals(False)
        self._scaleLabel.setText(f"{scale:.2f}x")

        # refresh rates
        try:
            primaryLoop = int(self.config.getValue("sprite.refreshRates.primaryLoop"))
        except Exception:
            primaryLoop = 30

        try:
            secondaryLoop = int(self.config.getValue("sprite.refreshRates.secondaryLoop"))
        except Exception:
            secondaryLoop = 15

        self._primaryLoopSpinBox.blockSignals(True)
        self._primaryLoopSpinBox.setValue(primaryLoop)
        self._primaryLoopSpinBox.blockSignals(False)

        self._secondaryLoopSpinBox.blockSignals(True)
        self._secondaryLoopSpinBox.setValue(secondaryLoop)
        self._secondaryLoopSpinBox.blockSignals(False)

        # permissions
        try:
            allowedGeoIpFetch = bool(self.config.getValue("location.allowedGeoIpFetch"))
        except Exception:
            allowedGeoIpFetch = False

        self._geoIpSwitch.blockSignals(True)
        self._geoIpSwitch.setChecked(allowedGeoIpFetch)
        self._geoIpStateLabel.setText("enabled" if allowedGeoIpFetch else "disabled")
        self._geoIpSwitch.blockSignals(False)

    def _reposition(self):
        """
        reposition the window anchored to the sprite with appropriate margins.
        """

        target = self.anchorNextToSprite(
            yAlign="bottom",
            preferredSide="right",
            margin=BORDER_MARGIN,
            occludersProvider=self.occludersProvider,
        )

        self.animateTo(target)

    def eventFilter(self, watched, event) -> bool:
        """
        filter events to close window on clicks outside the window or sprite.
        
        :param watched: the watched object
        :param event: the event to filter
        :return: whether the event was handled
        :rtype: bool
        """

        if (not self.isVisible()) or (not self.sprite):
            return False

        if event.type() == QEvent.ApplicationDeactivate:
            self.close()
            return False

        if event.type() != QEvent.MouseButtonPress:
            return False

        globalPos = event.globalPos()
        widget = QApplication.widgetAt(globalPos)

        if widget is None:
            self.close()
            return False

        if (widget is self) or (self.isAncestorOf(widget)):
            return False

        if (widget is self.sprite) or (self.sprite.isAncestorOf(widget)):
            return False

        if self.hatDropdown.isAncestorOf(widget) or (self.hatDropdown.view() and self.hatDropdown.view().isVisible()):
            return False

        self.close()
        return False

    def open(self) -> None:
        """
        open the settings window and sync controls from config.
        """

        super().open()
        self._syncFromConfig()
        QApplication.instance().installEventFilter(self)

    def hideEvent(self, event) -> None:
        """
        handle hide event by removing event filter.
        
        :param event: the hide event
        """

        try:
            QApplication.instance().removeEventFilter(self)
        finally:
            super().hideEvent(event)
