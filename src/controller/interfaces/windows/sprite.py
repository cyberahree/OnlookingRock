from ..base.anchor import SpriteAnchorMixin
from ..base import InterfaceComponent

from ..base.lookskit import (
    BodyLabel,
    CloseButton,
    Divider,
    SubheadingLabel,
    SurfaceFrame,
    applyRockStyle,
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
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QLineEdit,
)

from typing import Callable, Iterable, Optional

def clamp(value: float, minVal: float = 0.0, maxVal: float = 1.0) -> float:
    return max(minVal, min(maxVal, float(value)))

class SpriteWindowComponent(InterfaceComponent, SpriteAnchorMixin):
    def __init__(
        self,
        sprite: QWidget,
        clock,
        config: ConfigController,
        occludersProvider: Optional[Callable[[], Iterable[QWidget]]] = (lambda: []),
    ):
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
        rootLayout.addWidget(self._makeTextRow("User Nickname", key="userNick"))
        rootLayout.addWidget(Divider())

        # Scale slider
        rootLayout.addWidget(self._makeScaleSliderRow("Scale", key="scale"))
        rootLayout.addWidget(Divider())

        # Refresh Rates
        rootLayout.addWidget(BodyLabel("Refresh Rates", selectable=False))
        rootLayout.addWidget(self._makeRefreshRateSpinBox("Primary Loop", key="primaryLoop"))
        rootLayout.addWidget(self._makeRefreshRateSpinBox("Secondary Loop", key="secondaryLoop"))

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
                height: 6px;
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

    def _makeTextRow(self, label: str, *, key: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(PADDING // 2)

        nameLabel = BodyLabel(label, selectable=False)
        nameLabel.setFixedWidth(120)
        layout.addWidget(nameLabel, 0)

        textEdit = QLineEdit()
        textEdit.setMaxLength(32)
        layout.addWidget(textEdit, 1)

        self._nickEdit = textEdit

        def onChanged(text: str) -> None:
            self._applyKeyValue(key, text)

        textEdit.textChanged.connect(onChanged)
        return row

    def _makeScaleSliderRow(self, label: str, *, key: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(PADDING // 2)

        nameLabel = BodyLabel(label, selectable=False)
        nameLabel.setFixedWidth(74)
        layout.addWidget(nameLabel, 0)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(25, 200)  # 0.25 to 2.0
        slider.setSingleStep(5)
        slider.setPageStep(10)
        slider.setTracking(True)
        layout.addWidget(slider, 1)

        valueLabel = BodyLabel("1.0x")
        valueLabel.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        valueLabel.setFixedWidth(42)
        layout.addWidget(valueLabel, 0)

        self._scaleSlider = slider
        self._scaleLabel = valueLabel

        def onChanged(v: int) -> None:
            scale = v / 100.0
            self._scaleLabel.setText(f"{scale:.2f}x")

        def onReleased() -> None:
            scale = slider.value() / 100.0
            self._applyKeyValue(key, scale)

        slider.valueChanged.connect(onChanged)
        slider.sliderReleased.connect(onReleased)
        return row

    def _makeRefreshRateSpinBox(self, label: str, *, key: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(PADDING // 2)

        nameLabel = BodyLabel(label, selectable=False)
        nameLabel.setFixedWidth(120)
        layout.addWidget(nameLabel, 0)

        spinBox = QSpinBox()
        spinBox.setMinimum(1)
        spinBox.setMaximum(240)
        spinBox.setSingleStep(1)
        spinBox.setSuffix(" Hz")
        layout.addWidget(spinBox, 1)

        if key == "primaryLoop":
            self._primaryLoopSpinBox = spinBox
        else:
            self._secondaryLoopSpinBox = spinBox

        def onChanged(v: int) -> None:
            self._applyKeyValue(key, v)

        spinBox.valueChanged.connect(onChanged)
        return row

    def _applyKeyValue(self, key: str, value) -> None:
        # config + sound
        if key == "userNick":
            self.config.setValue("sprite.userNick", value)
        elif key == "scale":
            scale = clamp(value, 0.25, 2.0)
            self.config.setValue("sprite.scale", scale)
            self._scaleLabel.setText(f"{scale:.2f}x")
        elif key == "primaryLoop":
            self.config.setValue("sprite.refreshRates.primaryLoop", value)
        elif key == "secondaryLoop":
            self.config.setValue("sprite.refreshRates.secondaryLoop", value)

        self._scheduleSave()

    def _scheduleSave(self) -> None:
        # restart debounce timer
        self._saveTimer.stop()
        self._saveTimer.start()

    def _saveConfigNow(self) -> None:
        try:
            self.config.saveConfig()
        except Exception:
            pass

    def _syncFromConfig(self) -> None:
        # user nickname
        try:
            userNick = str(self.config.getValue("sprite.userNick"))
        except Exception:
            userNick = "<USERNAME>"

        self._nickEdit.blockSignals(True)
        self._nickEdit.setText(userNick)
        self._nickEdit.blockSignals(False)

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

    def _reposition(self):
        target = self.anchorNextToSprite(
            yAlign="bottom",
            preferredSide="right",
            margin=BORDER_MARGIN,
            occludersProvider=self.occludersProvider,
        )

        self.animateTo(target)

    def eventFilter(self, watched, event) -> bool:
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

        self.close()
        return False

    def open(self) -> None:
        super().open()
        self._syncFromConfig()
        QApplication.instance().installEventFilter(self)

    def hideEvent(self, event) -> None:
        try:
            QApplication.instance().removeEventFilter(self)
        finally:
            super().hideEvent(event)
