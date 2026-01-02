from ..base.anchor import SpriteAnchorMixin
from ..base import InterfaceComponent

from ..base.lookskit import (
    BodyLabel,
    CloseButton,
    Divider,
    MutedLabel,
    RockButton,
    SubheadingLabel,
    SurfaceFrame,
    applyRockStyle,
    make_spinbox_row,
)

from ..base.styling import (
    BACKGROUND_COLOR,
    BORDER_MARGIN,
    DEFAULT_FONT,
    PADDING,
    TEXT_COLOR,
    asRGB,
    CLOSE_STR
)

from ...scene.system import SceneSystem
from ...config import ConfigController
from ...asset import AssetController

from PySide6.QtCore import Qt, QEvent, QSize, QTimer
from PySide6.QtGui import QColor, QIcon, QPixmap

from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from typing import Callable, Iterable, Optional

class SceneWindowComponent(InterfaceComponent, SpriteAnchorMixin):
    def __init__(
        self,
        sprite: QWidget,
        clock,
        config: ConfigController,
        decorations: SceneSystem,
        occludersProvider: Optional[Callable[[], Iterable[QWidget]]] = (lambda: []),
    ):
        super().__init__(sprite, clock)

        self.config = config
        self.decorations = decorations
        self.occludersProvider = occludersProvider

        self.decorAssetController = AssetController("images/decorations")

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
        self.setObjectName("sceneWindow")
        self.setFixedWidth(360)

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

        self.titleLabel = SubheadingLabel("Scene")
        self.titleLabel.setObjectName("sceneTitle")
        headerLayout.addWidget(self.titleLabel, 1)

        self.closeButton = CloseButton(onClick=self.close)
        headerLayout.addWidget(self.closeButton, 0, Qt.AlignRight)

        rootLayout.addWidget(headerWidget)
        rootLayout.addWidget(Divider())

        # startup spawn count
        spawnRow, self.spawnSpin = make_spinbox_row(
            "Startup spawn",
            min_val=0,
            max_val=50,
            step=1,
            suffix=" decorations",
            on_changed=self._onSpawnChanged,
        )
        rootLayout.addWidget(spawnRow)
        rootLayout.addWidget(Divider())

        # decorations picker
        rootLayout.addWidget(BodyLabel("Add decorations", selectable=False))

        self.decorList = QListWidget()
        self.decorList.setObjectName("decorList")
        self.decorList.setIconSize(QSize(32, 32))
        self.decorList.setSpacing(2)
        self.decorList.itemDoubleClicked.connect(self._placeSelected)
        rootLayout.addWidget(self.decorList)

        buttonsRow = QWidget()
        buttonsLayout = QHBoxLayout(buttonsRow)
        buttonsLayout.setContentsMargins(0, 0, 0, 0)
        buttonsLayout.setSpacing(PADDING // 2)

        self.placeButton = RockButton("Place", variant="default", onClick=self._placeSelected)
        self.cancelButton = RockButton("Cancel", variant="ghost", onClick=self._cancelPlacement)
        buttonsLayout.addWidget(self.placeButton, 1)
        buttonsLayout.addWidget(self.cancelButton, 0)
        rootLayout.addWidget(buttonsRow)

        self.helpLabel = MutedLabel(
            f"Tip: while this window is open, decorations get a red {CLOSE_STR} you can click to delete."
        )
    
        rootLayout.addWidget(self.helpLabel)

        # style
        onHoverBackground = QColor(BACKGROUND_COLOR).darker(106)
        applyRockStyle(
            self,
            extraQss=f"""
            QLabel#sceneTitle {{
                color: {asRGB(TEXT_COLOR)};
                padding: 0px;
            }}

            QListWidget#decorList {{
                background: transparent;
                border: none;
                color: {asRGB(TEXT_COLOR)};
                outline: none;
            }}

            QListWidget#decorList::item {{
                border-radius: 4px;
                padding: 4px;
            }}

            QListWidget#decorList::item:selected {{
                color: {asRGB(TEXT_COLOR)};
                background-color: {asRGB(onHoverBackground)};
                border: 1px solid {asRGB(TEXT_COLOR)};
            }}

            QListWidget#decorList::item:hover {{
                background-color: {asRGB(onHoverBackground)};
            }}
            """,
        )

        self._populateDecorList()
        self._syncFromConfig()
    
    def _populateDecorList(self) -> None:
        self.decorList.clear()

        # build items from assets
        assets = sorted(
            [p for p in self.decorAssetController.listDirectory("")]
        )

        for path in assets:
            name = str(path.stem)
            pixmap = QPixmap(str(path))
            icon = QIcon(pixmap) if (not pixmap.isNull()) else QIcon()

            item = QListWidgetItem(icon, name)
            item.setData(Qt.UserRole, name)
            item.setFont(DEFAULT_FONT)
            self.decorList.addItem(item)

        # select first by default
        if self.decorList.count() > 0 and self.decorList.currentRow() < 0:
            self.decorList.setCurrentRow(0)
    
    def _syncFromConfig(self) -> None:
        try:
            value = int(self.config.getValue("scene.startupDecorationSpawnCount"))
        except Exception:
            value = 3

        self.spawnSpin.blockSignals(True)
        self.spawnSpin.setValue(max(0, value))
        self.spawnSpin.blockSignals(False)

    def _onSpawnChanged(self, value: int) -> None:
        self.config.setValue(
            "scene.startupDecorationSpawnCount",
            int(value)
        )

        self._scheduleSave()

    def _placeSelected(self) -> None:
        item = self.decorList.currentItem()
    
        if item is None:
            return

        name = item.data(Qt.UserRole) or item.text()

        if not name:
            return

        self.decorations.beginPlacement(str(name))

    def _cancelPlacement(self) -> None:
        self.decorations.endPlacement()

    def _scheduleSave(self) -> None:
        self._saveTimer.stop()
        self._saveTimer.start()

    def _saveConfigNow(self) -> None:
        try:
            self.config.saveConfig()
        except Exception:
            pass

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

        if event.type() != QEvent.MouseButtonPress:
            return False

        try:
            if self.decorations.editor.canEdit:
                return False
        except Exception:
            pass

        globalPos = event.globalPos()
        widget = QApplication.widgetAt(globalPos)

        # when the sprite loses focus: close
        if widget is None:
            self.close()
            return False

        if (widget is self) or (self.isAncestorOf(widget)):
            return False

        if (widget is self.sprite) or (self.sprite.isAncestorOf(widget)):
            return False

        # clicks on decoration viewports (placing/deleting) should not close
        try:
            window = widget.window()

            for viewport in getattr(self.decorations, "viewports", []):
                if (window is viewport) or (widget is viewport) or viewport.isAncestorOf(widget):
                    return False

        except Exception:
            pass

        # otherwise close
        self.close()
        return False

    def open(self) -> None:
        super().open()
        self._syncFromConfig()
        self.decorations.setEditMode(True)
        QApplication.instance().installEventFilter(self)

    def hideEvent(self, event) -> None:
        try:
            try:
                self.decorations.endPlacement()
            except Exception:
                pass

            try:
                self.decorations.setEditMode(False)
            except Exception:
                pass

            try:
                QApplication.instance().removeEventFilter(self)
            except Exception:
                pass
        finally:
            super().hideEvent(event)
