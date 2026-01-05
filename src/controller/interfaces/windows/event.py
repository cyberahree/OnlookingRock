from ...system.timings import TimingClock

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
    BORDER_RADIUS,
    DEFAULT_FONT,
    PADDING,
    TEXT_COLOR,
    asRGB,
)

from PySide6.QtCore import Qt, QSize, QEvent, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from typing import Callable, Iterable, Optional

# this only runs while the window is open
REFRESH_INTERVAL = 1000

class EventPickerWindowComponent(InterfaceComponent, SpriteAnchorMixin):
    """
    Window for picking and triggering sprite events manually.
    """

    def __init__(
        self,
        sprite: QWidget,
        clock: Optional[TimingClock],
        eventManager,
        occludersProvider: Optional[Callable[[], Iterable[QWidget]]] = (lambda: []),
    ):
        super().__init__(sprite, clock)

        self.eventManager = eventManager
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

        self._refreshTimer = QTimer(self)
        self._refreshTimer.setInterval(REFRESH_INTERVAL)
        self._refreshTimer.timeout.connect(self.refresh)

    def build(self) -> None:
        self.setObjectName("eventPicker")

        self.setFixedWidth(320)
        self.setMaximumHeight(512)

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

        self.titleLabel = SubheadingLabel("Events")
        self.titleLabel.setObjectName("eventTitle")
        headerLayout.addWidget(self.titleLabel, 1)

        self.closeButton = CloseButton(onClick=self.close)
        headerLayout.addWidget(self.closeButton, 0, Qt.AlignRight)

        rootLayout.addWidget(headerWidget)
        rootLayout.addWidget(Divider())

        self.hintLabel = SubheadingLabel(
            "click an event to run it - some might not play if the sprite is busy (getting dragged, yapping, etc..)",
            selectable=False,
        )

        self.hintLabel.setObjectName("eventHint")
        rootLayout.addWidget(self.hintLabel)
        rootLayout.addWidget(Divider())

        self.statusLabel = BodyLabel("", wrap=True, selectable=False)
        self.statusLabel.setObjectName("eventStatus")
        self.statusLabel.hide()
        rootLayout.addWidget(self.statusLabel)

        self.listWidget = QListWidget()
        self.listWidget.setObjectName("eventList")
        self.listWidget.setFont(DEFAULT_FONT)
        self.listWidget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.listWidget.setIconSize(QSize(16, 16))
        self.listWidget.setSpacing(0)
        self.listWidget.itemClicked.connect(self._onClicked)
        rootLayout.addWidget(self.listWidget)

        # style
        onHoverBackground = QColor(BACKGROUND_COLOR).darker(106)
        onSelectBackground = QColor(BACKGROUND_COLOR).darker(112)

        applyRockStyle(
            self,
            extraQss=f"""
            QLabel#eventTitle {{
                color: {asRGB(TEXT_COLOR)};
                padding: 0px;
            }}

            QLabel#eventHint {{
                color: rgba({TEXT_COLOR.red()}, {TEXT_COLOR.green()}, {TEXT_COLOR.blue()}, 170);
                padding: 0px;
            }}

            QLabel#eventStatus {{
                color: rgba({TEXT_COLOR.red()}, {TEXT_COLOR.green()}, {TEXT_COLOR.blue()}, 210);
                padding: 0px;
            }}

            QLabel#eventItemTitle {{
                color: {asRGB(TEXT_COLOR)};
                padding: 0px;
            }}

            QLabel#eventItemStatus {{
                color: rgba({TEXT_COLOR.red()}, {TEXT_COLOR.green()}, {TEXT_COLOR.blue()}, 170);
                padding: 0px;
            }}

            QListWidget#eventList {{
                background: transparent;
                border: none;
                color: {asRGB(TEXT_COLOR)};
                outline: none;
            }}

            QListWidget#eventList::item {{
                border-radius: {BORDER_RADIUS}px;
                padding: {PADDING // 2}px;
                min-height: {DEFAULT_FONT.pointSize() * 2}px;
            }}

            QListWidget#eventList::item:hover {{
                background-color: {asRGB(onHoverBackground)};
            }}

            QListWidget#eventList::item:selected {{
                background-color: {asRGB(onSelectBackground)};
            }}
            """,
        )

        self.refresh(fullRebuild=True)

    def open(self) -> None:
        self.ensureBuilt()
        self.refresh(fullRebuild=True)
        self._refreshTimer.start()
        return super().open()

    def close(self) -> bool:
        try:
            self._refreshTimer.stop()
        except Exception:
            pass

        return super().close()

    def hideEvent(self, event) -> None:
        try:
            self._refreshTimer.stop()
        except Exception:
            pass

        return super().hideEvent(event)

    def _buildItemWidget(self, title: str) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(PADDING // 2, PADDING // 3, PADDING // 2, PADDING // 2)
        layout.setSpacing(PADDING // 4)

        titleLabel = BodyLabel(title, wrap=False, selectable=False)
        titleLabel.setObjectName("eventItemTitle")
        titleLabel.setContentsMargins(0, 0, 0, PADDING // 6)

        statusLabel = SubheadingLabel("available")
        statusLabel.setObjectName("eventItemStatus")
        statusLabel.setMaximumHeight(DEFAULT_FONT.pointSize() + 2)

        layout.addWidget(titleLabel)
        layout.addWidget(statusLabel)

        return container

    def _createListItem(self, eventId, eventName: str) -> None:
        item = QListWidgetItem()
        item.setData(Qt.UserRole, eventId)
        item.setData(69420, eventName)

        widget = self._buildItemWidget(str(eventName))
        item.setSizeHint(widget.sizeHint())

        self.listWidget.addItem(item)
        self.listWidget.setItemWidget(item, widget)

    def _updateItemDisplay(self, item: QListWidgetItem) -> None:
        eventId = item.data(Qt.UserRole)
        eventName = item.data(69420) # lool

        widget = self.listWidget.itemWidget(item)

        if not widget:
            return

        titleLabel = widget.findChild(BodyLabel, "eventItemTitle")
        statusLabel = widget.findChild(SubheadingLabel, "eventItemStatus")

        if titleLabel:
            titleLabel.setText(
                "random" if eventId == "__random__" else str(eventName)
            )

        statusText = ""

        if eventId == "__random__":
            statusText = "pick a random event (if any available)"
        else:
            event = self.eventManager.getEvent(eventId)
            isEnabled = self.eventManager.isEventEnabled(eventId)
            cooldownTime = self.eventManager.getFriendlyCooldownText(eventId)

            if event is None: # ????
                statusText = "wtf"
            elif not isEnabled:
                statusText = "disabled"
            elif cooldownTime is not None:
                statusText = f"disabled until: {cooldownTime}"
            else:
                statusText = "available"

        if statusLabel:
            statusLabel.setText(statusText)

        try:
            item.setSizeHint(widget.sizeHint())
        except Exception:
            pass

    def refresh(self, fullRebuild: bool = False) -> None:
        """Refresh list labels (and optionally rebuild items)."""

        if not hasattr(self, "listWidget"):
            return

        if fullRebuild:
            self.listWidget.clear()

            # random option
            self._createListItem("__random__", "random")

            # discovered events
            events = self.eventManager.getEvents()

            for eventId, eventName in sorted(events, key=lambda s: str(s[0]).lower()):
                self._createListItem(eventId, eventName)

        # update labels in place
        for index in range(self.listWidget.count()):
            item = self.listWidget.item(index)

            if not item:
                continue

            self._updateItemDisplay(item)

        # sizing tweak
        try:
            self.listWidget.doItemsLayout()
        except Exception:
            pass

    def _flashStatus(self, text: str, ms: int = 2000) -> None:
        try:
            self.statusLabel.setText(text)
            self.statusLabel.show()
        except Exception:
            return

        QTimer.singleShot(ms, lambda: self.statusLabel.hide())

    def _onClicked(self, item: QListWidgetItem) -> None:
        if not item:
            return

        eventId = item.data(Qt.UserRole)

        # clear selection state quickly
        try:
            self.listWidget.clearSelection()
            self.listWidget.setCurrentRow(-1)
            self.listWidget.clearFocus()
            viewport = self.listWidget.viewport()
            QApplication.sendEvent(viewport, QEvent(QEvent.Leave))
            viewport.update()
        except Exception:
            pass

        if eventId == "__random__":
            # hide immediately so canRun gates won't be blocked by fade
            try:
                self.hide()
            except Exception:
                pass
            try:
                super().close()
            except Exception:
                pass
            QTimer.singleShot(0, lambda: self.eventManager.attemptEventTrigger())
            return

        # check cooldown locally; keep window open if still cooling down
        cooldownLabel = None
        try:
            cooldownLabel = self.eventManager.getFriendlyCooldownText(str(eventId))
        except Exception:
            cooldownLabel = None

        if cooldownLabel:
            self._flashStatus(cooldownLabel)
            self.refresh(fullRebuild=False)
            return

        # ready to run: hide immediately so canRun gates won't be blocked by fade
        try:
            self.hide()
        except Exception:
            pass
        try:
            super().close()
        except Exception:
            pass

        QTimer.singleShot(0, lambda: self.eventManager.triggerEvent(str(eventId)))

    def _reposition(self):
        target = self.anchorNextToSprite(
            yAlign="bottom",
            preferredSide="right",
            margin=BORDER_MARGIN,
            occludersProvider=self.occludersProvider,
        )

        self.animateTo(target)
