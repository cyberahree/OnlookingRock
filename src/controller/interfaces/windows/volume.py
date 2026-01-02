from ..base.anchor import SpriteAnchorMixin
from ..base import InterfaceComponent

from ..base.lookskit import (
    CloseButton,
    Divider,
    SubheadingLabel,
    SurfaceFrame,
    applyRockStyle,
    make_slider_row,
)

from ..base.styling import (
    BACKGROUND_COLOR,
    BORDER_MARGIN,
    DEFAULT_FONT,
    PADDING,
    TEXT_COLOR,
    asRGB,
)

from ...system.sound import SoundCategory, SoundManager
from ...config import ConfigController

from PySide6.QtCore import Qt, QEvent, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from typing import Callable, Iterable, Optional

def clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))

class VolumeWindowComponent(InterfaceComponent, SpriteAnchorMixin):
    def __init__(
        self,
        sprite: QWidget,
        clock,
        config: ConfigController,
        soundManager: SoundManager,
        occludersProvider: Optional[Callable[[], Iterable[QWidget]]] = (lambda: []),
    ):
        super().__init__(sprite, clock)

        self.config = config
        self.soundManager = soundManager
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

        # debounce config writes when dragging sliders
        self._saveTimer = QTimer(self)
        self._saveTimer.setSingleShot(True)
        self._saveTimer.setInterval(450)
        self._saveTimer.timeout.connect(self._saveConfigNow)

    def build(self) -> None:
        self.setObjectName("volumeWindow")

        self.setFixedWidth(276)

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

        self.titleLabel = SubheadingLabel("Volume")
        self.titleLabel.setObjectName("volumeTitle")
        headerLayout.addWidget(self.titleLabel, 1)

        self.closeButton = CloseButton(onClick=self.close)
        headerLayout.addWidget(self.closeButton, 0, Qt.AlignRight)

        rootLayout.addWidget(headerWidget)
        rootLayout.addWidget(Divider())

        # sliders
        self._rows: dict[str, tuple] = {}

        rootRow, rootSlider, rootLabel = make_slider_row(
            "Master",
            min_val=0,
            max_val=100,
            on_changed=lambda v: self._applyKeyVolume("master", v / 100.0),
            show_percentage=True,
        )

        self._rows["master"] = (rootSlider, rootLabel)
        rootLayout.addWidget(rootRow)
        rootLayout.addWidget(Divider())

        for cat in (
            SoundCategory.EVENT,
            SoundCategory.FEEDBACK,
            SoundCategory.AMBIENT,
            SoundCategory.SPECIAL,
            SoundCategory.SPEECH,
        ):
            catRow, catSlider, catLabel = make_slider_row(
                cat.name.title(),
                min_val=0,
                max_val=100,
                on_changed=lambda v, key=cat.name: self._applyKeyVolume(key, v / 100.0),
                show_percentage=True,
            )

            self._rows[cat.name] = (catSlider, catLabel)
            rootLayout.addWidget(catRow)

        # style
        onHoverBackground = QColor(BACKGROUND_COLOR).darker(106)
        applyRockStyle(
            self,
            extraQss=f"""
            QLabel#volumeTitle {{
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

    def _applyKeyVolume(self, key: str, value01: float) -> None:
        value01 = clamp(value01)

        # UI label
        _slider, label = self._rows.get(key, (None, None))

        if label is not None:
            label.setText(f"{int(round(value01 * 100))}%")

        # config + sound
        if key == "master":
            self.soundManager.setMasterVolume(value01)
            self.config.setValue("sound.masterVolume", value01)
        else:
            # key is category name
            self.soundManager.setCategoryVolume(key, value01)
            self.config.setValue(f"sound.categoryVolumes.{key}", value01)

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
        # master
        try:
            master = clamp(self.config.getValue("sound.masterVolume"))
        except Exception:
            master = 0.5

        slider, label = self._rows.get("master", (None, None))

        if slider is not None:
            slider.blockSignals(True)
            slider.setValue(int(round(master * 100)))
            slider.blockSignals(False)
        if label is not None:
            label.setText(f"{int(round(master * 100))}%")

        # categories
        try:
            categoryVolumes = dict(self.config.getValue("sound.categoryVolumes") or {})
        except Exception:
            categoryVolumes = {}

        for cat in (
            SoundCategory.EVENT,
            SoundCategory.FEEDBACK,
            SoundCategory.AMBIENT,
            SoundCategory.SPECIAL,
            SoundCategory.SPEECH,
        ):
            volume = clamp(
                categoryVolumes.get(
                    cat.name, self.soundManager.soundCategories[cat].volume
                )
            )

            slider, label = self._rows.get(cat.name, (None, None))

            if slider is not None:
                slider.blockSignals(True)
                slider.setValue(int(round(volume * 100)))
                slider.blockSignals(False)
            
            if label is not None:
                label.setText(f"{int(round(volume * 100))}%")
                
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
