from ..styling import (
    asRGB,
    BACKGROUND_COLOR,
    TEXT_COLOR,
    SUBHEADING_FONT,
    DEFAULT_FONT,
    BORDER_RADIUS,
    BORDER_MARGIN,
    PADDING,
)

from ..base import InterfaceComponent

from PySide6.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QAbstractItemView
)

from PySide6.QtCore import Qt, QPoint, QSize, QTimer
from PySide6.QtGui import QIcon, QColor

from typing import Callable, Optional, Sequence
from dataclasses import dataclass

SIZE_CONSTRAINTS = (260, 320)

@dataclass(frozen=True)
class MenuAction:
    name: str
    label: str
    callback: Callable[[], None]
    iconPath: Optional[str] = None

from ..styling import (
    asRGB,
    BACKGROUND_COLOR,
    TEXT_COLOR,
    SUBHEADING_FONT,
    DEFAULT_FONT,
    BORDER_RADIUS,
    BORDER_MARGIN,
    PADDING,
)

from ..base import InterfaceComponent

from PySide6.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QAbstractItemView
)

from PySide6.QtCore import Qt, QPoint, QSize, QTimer, QEvent, QRect
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QColor

from typing import Callable, Optional, Sequence
from dataclasses import dataclass

SIZE_CONSTRAINTS = (128, 512)

@dataclass(frozen=True)
class MenuAction:
    name: str
    label: str
    callback: Callable[[], None]
    iconPath: Optional[str] = None

class StartMenuComponent(InterfaceComponent):
    def __init__(
        self,
        sprite: QWidget,
        actions: Sequence[MenuAction],
        refreshRate: int = 10
    ):
        super().__init__(sprite, refreshRate)

        self.actions = list(actions)
        
        self.setWindowFlags(
            Qt.Tool |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )

        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFont(DEFAULT_FONT)

    def build(self) -> None:
        self.setObjectName("startMenu")

        self.setFixedWidth(SIZE_CONSTRAINTS[0])
        self.setMaximumHeight(SIZE_CONSTRAINTS[1])

        # main container
        self.rootFrame = QFrame(self)
        self.rootFrame.setObjectName("menuRoot")

        outerLayout = QVBoxLayout(self)
        outerLayout.setContentsMargins(0, 0, 0, 0)
        outerLayout.addWidget(self.rootFrame)

        self.rootLayout = QVBoxLayout(self.rootFrame)
        self.rootLayout.setContentsMargins(PADDING, PADDING, PADDING, PADDING)
        self.rootLayout.setSpacing(PADDING / 2)

        self.titleLabel = QLabel("Start Menu")
        self.titleLabel.setObjectName("menuTitle")
        self.titleLabel.setFont(SUBHEADING_FONT)
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

            if action.iconPath:
                item.setIcon(QIcon(action.iconPath))

            self.listWidget.addItem(item)

        self.listWidget.itemClicked.connect(self._onClicked)

        self.rootLayout.addWidget(self.titleLabel)
        self.rootLayout.addWidget(self.listWidget)

        # bubble-like stylesheet
        onHoverBackground = QColor(BACKGROUND_COLOR).darker(106)
        onSelectBackground = QColor(BACKGROUND_COLOR).darker(112)

        self.setStyleSheet(f"""
        QFrame#menuRoot {{
            background-color: {asRGB(BACKGROUND_COLOR)};
            border-radius: {BORDER_RADIUS}px;
        }}

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
        """)

        # update height
        QTimer.singleShot(0, self._recomputeHeight)
    
    def _getSpriteGlobalBounds(self) -> QRect:
        topLeft = self.sprite.mapToGlobal(QPoint(0, 0))

        return QRect(
            topLeft,
            self.sprite.size()
        )

    def _recomputeHeight(self) -> None:
        if not hasattr(self, "listWidget"):
            return

        self.listWidget.doItemsLayout()
        listCount = self.listWidget.count()

        # collect height of all list rows
        rowsTotalHeight = 0
        if listCount > 0:
            for i in range(listCount):
                h = self.listWidget.sizeHintForRow(i)

                if h > 0:
                    rowsTotalHeight += h

            # spacing between rows
            rowsTotalHeight += self.listWidget.spacing() * max(0, listCount - 1)

        titleHeight = self.titleLabel.sizeHint().height()
        chromeHeight = (PADDING * 2) + titleHeight + self.rootLayout.spacing()

        maxListHeight = max(0, SIZE_CONSTRAINTS[1] - chromeHeight)

        if rowsTotalHeight <= maxListHeight:
            self.listWidget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            listHeight = max(rowsTotalHeight, 1)  # avoid 0-height funkiness
            menuHeight = chromeHeight + listHeight
        else:
            self.listWidget.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            listHeight = maxListHeight
            menuHeight = SIZE_CONSTRAINTS[1]

        self.listWidget.setFixedHeight(listHeight)
        self.setFixedHeight(menuHeight)

        # reposition because size changed
        self._reposition()

    def _reposition(self):
        if not self.sprite:
            return
        
        screen = self.sprite.screen().availableGeometry()
        sprite = self.sprite.frameGeometry()

        width, height = self.width(), self.height()

        x = sprite.right() + BORDER_MARGIN
        y = sprite.bottom() - height

        if x + width > screen.right() - BORDER_MARGIN:
            x = sprite.left() - width - BORDER_MARGIN
        
        if y < screen.top() + BORDER_MARGIN:
            y = screen.top()

        if y + height > screen.bottom() - BORDER_MARGIN:
            y = screen.bottom() - height - BORDER_MARGIN
        
        # final clamp
        position = QPoint(x, y)
        position = self.clampToScreen(position)

        self.move(position)

    def _onClicked(self, item: QListWidgetItem) -> None:
        if not item.flags():
            return

        actionName = item.data(Qt.UserRole)
        
        for action in self.actions:
            if action.name != actionName:
                continue

            self.close()
            action.callback()
            break
    
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

        # we are not interested in clicks inside ourselves or the sprite
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
        QApplication.instance().installEventFilter(self)
        QTimer.singleShot(0, self._recomputeHeight)

    def hideEvent(self, event) -> None:
        try:
            QApplication.instance().removeEventFilter(self)
        finally:
            super().hideEvent(event)
