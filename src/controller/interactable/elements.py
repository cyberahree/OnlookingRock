from .styling import (
    asRGB,
    BACKGROUND_COLOR,
    TEXT_COLOR,
    HEADING_FONT,
    BORDER_RADIUS,
    BORDER_MARGIN,
    PADDING
)

from PySide6.QtCore import Qt, Signal

from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QDialog,
    QDialogButtonBox,
    QPushButton
)

def makeShutdownButton(visible: bool) -> tuple[QPushButton, Signal]:
    closeSignal = Signal()

    closeButton = QPushButton("x")
    closeButton.setVisible(visible)
    closeButton.setCursor(Qt.PointingHandCursor)
    closeButton.setFocusPolicy(Qt.NoFocus)
    closeButton.setFixedSize(28, 28)
    closeButton.clicked.connect(closeSignal.emit)

    tr, tg, tb, _ = TEXT_COLOR.getRgb()
    hover = f"rgba({tr}, {tg}, {tb}, 18)"
    pressed = f"rgba({tr}, {tg}, {tb}, 28)"

    closeButton.setStyleSheet(f"""
        QPushButton {{
            color: {asRGB(TEXT_COLOR)};
            background-color: transparent;
            border: 1px solid {asRGB(TEXT_COLOR)};
            border-radius: 6px;
            font-size: 14px;
            padding: 4px 12px;
        }}
        QPushButton:hover {{
            background: {hover};
        }}
        QPushButton:pressed {{
            background: {pressed};
        }}
    """)

    return closeButton, closeSignal

class StyledPanel(QWidget):
    def __init__(self, title: str, showCloseButton: bool = True):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(PADDING)

        headerRow = QHBoxLayout()
        headerRow.setContentsMargins(BORDER_MARGIN, BORDER_MARGIN, BORDER_MARGIN, 0)
        headerRow.setSpacing(PADDING)

        header = QLabel(title)
        header.setFont(HEADING_FONT)
        header.setStyleSheet("color: " + asRGB(TEXT_COLOR) + f"; padding: {BORDER_MARGIN}px;")

        headerRow.addWidget(header, 1)

        self.bodyFrame = QFrame()
        self.bodyFrame.setStyleSheet(f"""
            QFrame {{
                background-color: {asRGB(BACKGROUND_COLOR)};
                border-radius: {BORDER_RADIUS}px;
                padding: {PADDING}px;
            }}
        """)

        self.closeButton, self.closeSignal = makeShutdownButton(showCloseButton)
        headerRow.addWidget(self.closeButton, 0)

        self.bodyLayout = QVBoxLayout(self.bodyFrame)
        self.bodyLayout.setContentsMargins(BORDER_MARGIN, BORDER_MARGIN, BORDER_MARGIN, BORDER_MARGIN)
        self.bodyLayout.setSpacing(PADDING)

        layout.addWidget(header)
        layout.addWidget(self.bodyFrame)

class StyledModal(QDialog):
    def __init__(
            self,
            parent: QWidget,
            title: str,
            content: QWidget
        ):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Dialog
        )

        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)

        cardFrame = QFrame(self)
        cardFrame.setObjectName("cardFrame")

        titleLabel = QLabel(title)
        titleLabel.setFont(HEADING_FONT)
        titleLabel.setStyleSheet("color: " + asRGB(TEXT_COLOR) + f"; padding-bottom: {PADDING}px;")

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            cardFrame
        )

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        innerLayout = QVBoxLayout(cardFrame)
        innerLayout.setContentsMargins(BORDER_MARGIN, BORDER_MARGIN, BORDER_MARGIN, BORDER_MARGIN)
        innerLayout.setSpacing(PADDING)

        bodyWrap = QFrame(cardFrame)
        bodyWrap.setStyleSheet("QFrame { background: transparent; }")

        self.bodyLayout = QVBoxLayout(bodyWrap)
        self.bodyLayout.setContentsMargins(0, 0, 0, 0)
        self.bodyLayout.addWidget(content)

        innerLayout.addWidget(titleLabel)
        innerLayout.addWidget(bodyWrap, 1)
        innerLayout.addWidget(buttons)

        cardFrame.setStyleSheet(f"""
            QFrame#cardFrame {{
                background-color: {asRGB(BACKGROUND_COLOR)};
                border-radius: {BORDER_RADIUS}px;
            }}
        """)

        outerLayout = QVBoxLayout(self)
        outerLayout.setContentsMargins(0, 0, 0, 0)
        outerLayout.addWidget(cardFrame)

        self.resize(520, 320)
