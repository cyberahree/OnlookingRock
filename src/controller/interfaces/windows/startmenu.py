from ..base.anchor import SpriteAnchorMixin
from ..base import InterfaceComponent

from ..base.styling import (
    ACTION_ACCENT,
    BACKGROUND_COLOR,
    BORDER_MARGIN,
    BORDER_RADIUS,
    DEFAULT_FONT,
    ICON_ASSETS,
    PADDING,
    TEXT_COLOR,
    asRGB,
)

from ..base.lookskit import SubheadingLabel, SurfaceFrame, applyRockStyle

from PySide6.QtCore import Qt, QPoint, QSize, QEvent, QRect, QTimer
from PySide6.QtGui import QIcon, QColor

from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from typing import Callable, Iterable, Optional, Sequence
from dataclasses import dataclass

SIZE_CONSTRAINTS = (128, 512)

@dataclass
class MenuAction:
    name: str
    label: str
    callback: Callable[[], None]
    iconName: Optional[str] = None

class StartMenuComponent(InterfaceComponent, SpriteAnchorMixin):
    def __init__(
        self,
        sprite: QWidget,
        actions: Sequence[MenuAction],
        clock,
        occludersProvider: Optional[Callable[[], Iterable[QWidget]]] = (lambda: []),
    ):
        super().__init__(sprite, clock)

        self.actions = list(actions)
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
        self.isOpening = False

    def build(self) -> None:
        self.setObjectName("startMenu")

        self.setFixedWidth(SIZE_CONSTRAINTS[0])
        self.setMaximumHeight(SIZE_CONSTRAINTS[1])

        self.rootFrame = SurfaceFrame(self, padding=PADDING)
        self.rootFrame.setObjectName("menuRoot")

        outerLayout = QVBoxLayout(self)
        outerLayout.setContentsMargins(0, 0, 0, 0)
        outerLayout.addWidget(self.rootFrame)

        self.rootLayout = self.rootFrame.layout()

        self.titleLabel = SubheadingLabel("Start Menu")
        self.titleLabel.setObjectName("menuTitle")
        self.titleLabel.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.listWidget = QListWidget()
        self.listWidget.setObjectName("menuList")
        self.listWidget.setFont(DEFAULT_FONT)
        self.listWidget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.listWidget.setIconSize(QSize(16, 16))
        self.listWidget.setSpacing(0)

        for action in self.actions:
            item = QListWidgetItem(action.label)
            item.setData(Qt.UserRole, action.name)

            if action.iconName:
                path = ICON_ASSETS.blindGetAsset(action.iconName)
                item.setIcon(QIcon(str(path)))

            self.listWidget.addItem(item)

        self.listWidget.itemClicked.connect(self._onClicked)

        self.rootLayout.addWidget(self.titleLabel)
        self.rootLayout.addWidget(self.listWidget)

        onHoverBackground = QColor(BACKGROUND_COLOR).darker(106)
        onSelectBackground = QColor(BACKGROUND_COLOR).darker(112)

        applyRockStyle(
            self,
            extraQss=f"""
            QLabel#menuTitle {{
                color: {asRGB(TEXT_COLOR)};
                padding: 0px;
            }}

            QListWidget#menuList {{
                background: transparent;
                border: none;
                color: {asRGB(TEXT_COLOR)};
                outline: none;
            }}

            QListWidget#menuList::item {{
                border-radius: {BORDER_RADIUS}px;
                padding: 0px;
                min-height: {DEFAULT_FONT.pointSize()}px;
            }}

            QListWidget#menuList::item:hover {{
                background-color: {asRGB(onHoverBackground)};
            }}

            QListWidget#menuList::item:selected {{
                background-color: {asRGB(onSelectBackground)};
            }}
            """,
        )

    def _getSpriteGlobalBounds(self) -> QRect:
        topLeft = self.sprite.mapToGlobal(QPoint(0, 0))

        return QRect(
            topLeft,
            self.sprite.size(),
        )

    def _recomputeHeight(self) -> None:
        if not hasattr(self, "listWidget"):
            return

        self.listWidget.doItemsLayout()
        listCount = self.listWidget.count()

        rowsTotalHeight = 0

        if listCount > 0:
            for i in range(listCount):
                h = self.listWidget.sizeHintForRow(i)

                if h > 0:
                    rowsTotalHeight += h

            rowsTotalHeight += self.listWidget.spacing() * max(0, listCount - 1)

        titleHeight = self.titleLabel.sizeHint().height()
        chromeHeight = (PADDING * 2) + titleHeight + self.rootLayout.spacing()
        maxListHeight = max(0, SIZE_CONSTRAINTS[1] - chromeHeight)

        if rowsTotalHeight <= maxListHeight:
            self.listWidget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            listHeight = max(rowsTotalHeight, 1)
            menuHeight = chromeHeight + listHeight
        else:
            self.listWidget.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            listHeight = maxListHeight
            menuHeight = SIZE_CONSTRAINTS[1]

        self.listWidget.setFixedHeight(listHeight)
        self.setFixedHeight(menuHeight)

        self._reposition()

    def _resetListVisualState(self) -> None:
        if not hasattr(self, "listWidget"):
            return

        listWidget = self.listWidget

        listWidget.clearSelection()
        listWidget.setCurrentRow(-1)
        listWidget.clearFocus()

        viewport = listWidget.viewport()
        QApplication.sendEvent(viewport, QEvent(QEvent.Leave))
        viewport.update()

    def _onClicked(self, item: QListWidgetItem) -> None:
        if not item.flags():
            return

        actionName = item.data(Qt.UserRole)
        self._resetListVisualState()

        for action in self.actions:
            if action.name != actionName:
                continue

            self.close()
            action.callback()
            break

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

    def _recomputeHeightSnap(self) -> None:
        if not self.isVisible():
            return

        previous = self.enableMoveAnimation
        self.enableMoveAnimation = False

        try:
            self._recomputeHeight()
        finally:
            self.enableMoveAnimation = previous

    def open(self) -> None:
        super().open()
        QApplication.instance().installEventFilter(self)
        QTimer.singleShot(0, self._recomputeHeightSnap)

    def hideEvent(self, event) -> None:
        self._resetListVisualState()

        try:
            QApplication.instance().removeEventFilter(self)
        finally:
            super().hideEvent(event)

