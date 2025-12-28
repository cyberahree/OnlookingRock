from .registry import PanelRegistry, MenuEntry

from .styling import (
    asRGB,
    BACKGROUND_COLOR,
    TEXT_COLOR,
    HEADING_FONT,
    DEFAULT_FONT,
    BORDER_RADIUS,
    BORDER_MARGIN,
    PADDING,
    ANIMATION_OPACITY_DURATION
)

from PySide6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve, QEvent
from PySide6.QtGui import QIcon

from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QWidget,
    QStackedWidget,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QGraphicsOpacityEffect,
    QDialog,
)

class SpriteStartMenu(QWidget):
    def __init__(
        self,
        sprite: QWidget,
        registry: PanelRegistry,
        refreshRate: int = 10
    ):
        super().__init__(None)

        self.Sprite = sprite
        self.Registry = registry
        self.refreshRate = refreshRate

        self.isShuttingDown = False
        self.lastPanelRow = 0

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )

        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.StrongFocus)

        # window opacity effect and animation
        self.windowOpacityEffect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.windowOpacityEffect)
        self.windowOpacityEffect.setOpacity(0.0)

        self.fadeAnimation = QPropertyAnimation(
            self.windowOpacityEffect,
            b"opacity"
        )

        self.fadeAnimation.setEasingCurve(QEasingCurve.OutCubic)
        self.fadeAnimation.setDuration(ANIMATION_OPACITY_DURATION)
        self.fadeAnimation.finished.connect(self._onFadeFinished)

        # movement animation
        self.movementAnimation = QPropertyAnimation(self, b"pos")
        self.movementAnimation.setEasingCurve(QEasingCurve.OutCubic)

        # align to sprite
        self.followTimer = QTimer(self)
        self.followTimer.timeout.connect(self._reposition)
        self.followTimer.start(1000 // self.refreshRate)

        # click outside to close
        QApplication.instance().installEventFilter(self)

        # inner card
        self.cardFrame = QFrame(self)
        self.cardFrame.setObjectName("startMenuCardFrame")
        self.cardFrame.setContentsMargins(0, 0, 0, 0)

        # title
        self.titleLabel = QLabel("Menu", self.cardFrame)
        self.titleLabel.setFont(HEADING_FONT)
        self.titleLabel.setStyleSheet("color: " + asRGB(TEXT_COLOR) + f"; padding: {BORDER_MARGIN}px;")

        # list
        self.listWidget = QListWidget(self.cardFrame)
        self.stackWidget = QStackedWidget(self.cardFrame)

        self.listWidget.currentRowChanged.connect(self._onRowChanged)
        self.listWidget.setFixedWidth(256)

        # layouts
        bodyLayout = QHBoxLayout()
        bodyLayout.setContentsMargins(0, 0, 0, 0)
        bodyLayout.setSpacing(PADDING)

        bodyLayout.addWidget(self.listWidget)
        bodyLayout.addWidget(self.stackWidget, 1)

        cardLayout = QVBoxLayout(self.cardFrame)
        cardLayout.setContentsMargins(0, 0, 0, 0)
        cardLayout.setSpacing(0)

        cardLayout.addWidget(self.titleLabel)
        cardLayout.addLayout(bodyLayout)

        # outer layout
        outerLayout = QVBoxLayout(self)
        outerLayout.setContentsMargins(0, 0, 0, 0)
        outerLayout.addWidget(self.cardFrame)

        # apply styles
        self._applyStyle()
        self._populateEntries()

        self.hide()
    
    def _applyStyle(self):
        backgroundColour = asRGB(BACKGROUND_COLOR)
        foregroundColour = asRGB(TEXT_COLOR)

        # derive subtle UI tones from TEXT_COLOR (no extra theme constants needed)
        tr, tg, tb, _ = TEXT_COLOR.getRgb()
        border = f"rgba({tr}, {tg}, {tb}, 55)"
        hover = f"rgba({tr}, {tg}, {tb}, 18)"
        selected = f"rgba({tr}, {tg}, {tb}, 28)"
        pressed = f"rgba({tr}, {tg}, {tb}, 36)"
        divider = f"rgba({tr}, {tg}, {tb}, 25)"

        self.listWidget.setFont(DEFAULT_FONT)
        self.stackWidget.setFont(DEFAULT_FONT)

        self.cardFrame.setStyleSheet(f"""
            QFrame#startMenuCardFrame {{
                background-color: {backgroundColour};
                border: 1px solid {border};
                border-radius: {BORDER_RADIUS}px;
            }}

            QLabel {{
                color: {foregroundColour};
            }}

            QListWidget {{
                background: transparent;
                border: none;
                padding: {PADDING}px;
                outline: none;
            }}

            QListWidget::item {{
                color: {foregroundColour};
                padding: {PADDING}px {PADDING}px;
                margin: 2px 0px;
                border-radius: {BORDER_RADIUS}px;
            }}

            QListWidget::item:hover {{
                background-color: {hover};
            }}

            QListWidget::item:selected {{
                background-color: {selected};
            }}

            QListWidget::item:selected:active {{
                background-color: {pressed};
            }}

            QStackedWidget {{
                background: transparent;
            }}

            /* optional: nicer scrollbars that still follow your palette */
            QScrollBar:vertical {{
                background: transparent;
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {divider};
                border-radius: 5px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {selected};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """)

    
    def _populateEntries(self):
        self.listWidget.clear()

        for entry in self.Registry.getEntries():
            item = QListWidgetItem(
                (entry.icon or QIcon()),
                entry.title
            )
            item.setData(Qt.UserRole, entry.id)
            self.listWidget.addItem(item)
        
        if self.listWidget.count():
            # TODO: set final row
            self.listWidget.setCurrentRow(0)
    
    # public methods
    def toggleVisibility(self):
        if self.isVisible():
            self.closeStartMenu()
        else:
            self.openStartMenu()

    def openStartMenu(self):
        if self.isShuttingDown:
            return
        
        self._reposition(force_show=True)

        self.show()
        self.fadeAnimation.stop()
        self.windowOpacityEffect.setOpacity(0.0)
        self.fadeAnimation.setStartValue(0.0)
        self.fadeAnimation.setEndValue(1.0)
        self.fadeAnimation.start()

        self.listWidget.setFocus()
        self.activateWindow()
        self.raise_()
    
    def closeStartMenu(self):
        if self.isShuttingDown:
            return
        
        self.fadeAnimation.stop()
        self.fadeAnimation.setStartValue(self.windowOpacityEffect.opacity())
        self.fadeAnimation.setEndValue(0.0)
        self.fadeAnimation.start()
    
    def shutdown(self):
        self.isShuttingDown = True
        self.followTimer.stop()
        self.fadeAnimation.stop()
        self.movementAnimation.stop()

        try:
            QApplication.instance().removeEventFilter(self)
        except Exception:
            pass

        self.hide()

    # event methods
    def _onFadeFinished(self):
        if self.windowOpacityEffect.opacity() > 0.001:
            return
        
        self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.closeStartMenu()
            return
        
        super().keyPressEvent(event)

    def eventFilter(self, watched, event) -> bool:
        if self.isShuttingDown:
            return False

        if not self.isVisible():
            return False
        
        # check for mouse press
        if event.type() != QEvent.MouseButtonPress:
            return False
        
        globalPos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()

        # check if click is inside menu
        if self.geometry().contains(globalPos):
            return False
        
        self.closeStartMenu()
        return True
    
    # selection logic
    def _onRowChanged(self, currentRow: int) -> None:
        item = self.listWidget.item(currentRow)

        if not item:
            return
        
        entryID = item.data(Qt.UserRole)
        entry = self.Registry.getEntry(entryID)

        if not entry:
            return
        
        if entry.kind == "modal":
            self.listWidget.blockSignals(True)
            self.listWidget.setCurrentRow(self.lastPanelRow)
            self.listWidget.blockSignals(False)

            self._openModal(entry)
            return
    
        self.lastPanelRow = currentRow
        self._showPanel(entry)
    
    def _showPanel(self, entry: MenuEntry) -> None:
        if not entry.panel_factory:
            return
        
        # singleton cache
        if not hasattr(self, "_panelCache"):
            self._panelCache: dict[str, QWidget] = {}
        
        if entry.singleton and (entry.id in self._panelCache):
            panel = self._panelCache[entry.id]
        else:
            panel = entry.panel_factory()

            if entry.singleton:
                self._panelCache[entry.id] = panel

        if hasattr(panel, "closeRequested"):
            if not hasattr(self, "_panelCloseHooked"):
                self._panelCloseHooked: set[int] = set()

            panelId = id(panel)

            if panelId not in self._panelCloseHooked:
                panel.closeRequested.connect(self.closeStartMenu)
                self._panelCloseHooked.add(panelId)

        index = self.stackWidget.indexOf(panel)

        if index == -1:
            self.stackWidget.addWidget(panel)
            index = self.stackWidget.indexOf(panel)

        self.stackWidget.setCurrentIndex(index)

    def _openModal(self, entry: MenuEntry) -> None:
        if not entry.modal_factory:
            return
        
        # singleton cache
        if not hasattr(self, "_modalCache"):
            self._modalCache: dict[str, QDialog] = {}
        
        if entry.singleton and (entry.id in self._modalCache):
            modal = self._modalCache[entry.id]
        else:
            modal = entry.modal_factory(self)

            if entry.singleton:
                self._modalCache[entry.id] = modal
        
        self.hide()
        modal.exec()
    
    # repositioning
    def _reposition(self, force_show: bool = False):
        if not self.Sprite:
            return

        if self.isHidden() and not force_show:
            return
        
        screen = self.Sprite.screen().availableGeometry()
        sprite = self.Sprite.frameGeometry()

        self.adjustSize()
        self.cardFrame.adjustSize()

        width, height = self.width(), self.height()

        x = sprite.right() + BORDER_MARGIN
        y = sprite.top()

        # flip if need be
        if sprite.center().x() > screen.center().x():
            x = sprite.left() - width - BORDER_MARGIN
        
        if sprite.center().y() > screen.center().y():
            y = sprite.bottom() - height
        
        # clamp to screen
        x = max(
            screen.left() + BORDER_MARGIN,
            min(x, screen.right() - width - BORDER_MARGIN)
        )

        y = max(
            screen.top() + BORDER_MARGIN,
            min(y, screen.bottom() - height - BORDER_MARGIN)
        )

        if self.isHidden():
            self.move(x, y)
        else:
            self._animateTo(QPoint(x, y))

    def _animateTo(self, target: QPoint):
        if (self.pos() - target).manhattanLength() < 2:
            self.move(target)
            return

        if self.movementAnimation.state() == QPropertyAnimation.Running:
            self.movementAnimation.stop()

        distance = (self.pos() - target).manhattanLength()

        self.movementAnimation.setDuration(min(260, max(80, distance)))
        self.movementAnimation.setStartValue(self.pos())
        self.movementAnimation.setEndValue(target)
        self.movementAnimation.start()
