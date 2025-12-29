from ..styling import (
    asRGB,
    BACKGROUND_COLOR,
    TEXT_COLOR,
    DEFAULT_FONT,
    SUBHEADING_FONT,
    BORDER_RADIUS,
    PADDING
)

from ...config import (
    ConfigController,
    readJSONFile,
    deepMerge,
    pruneForDefaults,
    atomicWriteJson,
    getByPath,
    setByPath
)

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QTabWidget, QWidget, QFormLayout, QLineEdit, QSlider, QDoubleSpinBox,
    QMessageBox, QInputDialog
)

from PySide6.QtCore import Qt

from typing import Any, Callable, Optional

import copy

def _floatToSlider(
    value: float,
    min: float,
    step: float
) -> int:
    return int(round((value - min) / step))

def _sliderToFloat(
    position: int,
    min: float,
    step: float
) -> float:
    return float(min + (position * step))

class SettingsModal(QDialog):
    def __init__(
        self,
        parent: QWidget,
        config: ConfigController,
        onApplied: Optional[Callable[[dict[str, Any], str], None]] = None
    ):
        super().__init__(parent)

        self.setWindowTitle("Settings")
        self.setWindowFlags(
            Qt.Dialog |
            Qt.WindowStaysOnTopHint
        )

        self.setModal(True)

        self.setFont(DEFAULT_FONT)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {asRGB(BACKGROUND_COLOR)};
                color: {asRGB(TEXT_COLOR)};
                border-radius: {BORDER_RADIUS}px;
            }}
            QLabel {{
                color: {asRGB(TEXT_COLOR)};
            }}
        """)

        self.config = config
        self.schema = config.schema
        self.onApplied = onApplied or (lambda _cfg, _profile: None)

        self.selectedProfile = config.getActiveProfile()
        self.workingConfig = copy.deepcopy(config.config)
        self.dirty = False

        self._build()
        self._loadProfilesIntoCombo()
        self._rebuildTabs()

    def _build(self) -> None:
        rootLayout = QVBoxLayout(self)
        rootLayout.setContentsMargins(PADDING, PADDING, PADDING, PADDING)
        rootLayout.setSpacing(PADDING)

        # top bar
        topBar = QHBoxLayout()
        topBar.setSpacing(PADDING)

        title = QLabel("Settings")
        title.setFont(SUBHEADING_FONT)

        topBar.addWidget(title)
        topBar.addStretch(1)

        topBar.addWidget(QLabel("Profile:"))

        self.profileCombo = QComboBox()
        self.profileCombo.currentTextChanged.connect(
            self._onProfileChanged
        )

        self.newProfileButton = QPushButton("New")
        self.newProfileButton.clicked.connect(
            self._onNewProfileClicked
        )

        self.deleteProfileButton = QPushButton("Delete")
        self.deleteProfileButton.clicked.connect(
            self._onDeleteProfileClicked
        )

        topBar.addWidget(self.profileCombo)
        topBar.addWidget(self.newProfileButton)
        topBar.addWidget(self.deleteProfileButton)

        rootLayout.addLayout(topBar)

        # tabs
        self.tabs = QTabWidget()
        rootLayout.addWidget(self.tabs, 1)

        # bottom bar
        bottomBar = QHBoxLayout()
        bottomBar.addStretch(1)

        self.applyButton = QPushButton("Apply")
        self.applyButton.clicked.connect(
            self._onApplyClicked
        )

        self.saveButton = QPushButton("Save")
        self.saveButton.clicked.connect(
            self._onSaveClicked
        )

        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(
            self._onCancelClicked
        )

        bottomBar.addWidget(self.applyButton)
        bottomBar.addWidget(self.saveButton)
        bottomBar.addWidget(self.cancelButton)

    def _loadProfilesIntoCombo(self) -> None:
        self.profileCombo.blockSignals(True)

        try:
            self.profileCombo.clear()

            for profileName in self.config.getProfileNames():
                self.profileCombo.addItem(profileName)
            
            index = self.profileCombo.findText(
                self.selectedProfile
            )

            if index < 0:
                self.profileCombo.addItem(self.selectedProfile)
                index = self.profileCombo.findText(
                    self.selectedProfile
                )

            self.profileCombo.setCurrentIndex(index)
        finally:
            self.profileCombo.blockSignals(False)
    
    def _rebuildTabs(self) -> None:
        self.tabs.clear()

        sections = self.schema.get("sections", [])

        for section in sections:
            tab = QWidget()
            formLayout = QFormLayout(tab)
            formLayout.setContentsMargins(PADDING, PADDING, PADDING, PADDING)
            formLayout.setSpacing(PADDING)

            for item in section.get("items", []):
                path = item["path"]
                label = item.get("label", path)
                widget = self._buildItemWidget(item)
                formLayout.addRow(label, widget)

            self.tabs.addTab(tab, section.get("title", "Section"))

    def _buildItemWidget(
        self,
        item: dict[str, Any]
    ) -> QWidget:
        widgetType = item.get("widget")
        itemPath = item["path"]
        itemType = item.get("type")

        if widgetType == "lineedit" and itemType == "string":
            lineEdit = QLineEdit()

            lineEdit.setText(str(getByPath(self.workingConfig, itemPath)))
            lineEdit.textChanged.connect(lambda v, p=itemPath: self._setWorking(p, v))

            return lineEdit
    
        if widgetType == "combo" and itemType == "enum":
            options = item.get("options", [])

            comboBox = QComboBox()
            comboBox.addItems([str(o) for o in options])

            current = str(getByPath(self.workingConfig, itemPath))
            index = comboBox.findText(current)

            comboBox.setCurrentIndex(index if index >= 0 else 0)
            comboBox.currentTextChanged.connect(lambda v, p=itemPath: self._setWorking(p, v))

            return comboBox

        if widgetType == "slider" and itemType == "float":
            stepIncrement = float(item.get("step", 0.1))
            valueMin = float(item.get("min", 0.0))
            valueMax = float(item.get("max", 1.0))

            current = float(
                getByPath(self.workingConfig, itemPath)
            )

            container = QWidget()
            rowLayout = QHBoxLayout(container)
            rowLayout.setContentsMargins(0, 0, 0, 0)
            rowLayout.setSpacing(PADDING // 2)

            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(0)
            slider.setMaximum(max(0, _floatToSlider(valueMax, valueMin, stepIncrement)))
            slider.setValue(_floatToSlider(current, valueMin, stepIncrement))

            spinBox = QDoubleSpinBox()
            spinBox.setMinimum(valueMin)
            spinBox.setMaximum(valueMax)
            spinBox.setSingleStep(stepIncrement)
            spinBox.setDecimals(4)
            spinBox.setValue(current)

            def setFromSlider(pos: int) -> None:
                val = _sliderToFloat(pos, valueMin, stepIncrement)
                spinBox.blockSignals(True)

                try:
                    spinBox.setValue(val)
                finally:
                    spinBox.blockSignals(False)

                self._setWorking(itemPath, float(val))

            def setFromSpinBox(val: float) -> None:
                pos = _floatToSlider(float(val), valueMin, stepIncrement)
                slider.blockSignals(True)

                try:
                    slider.setValue(pos)
                finally:
                    slider.blockSignals(False)

                self._setWorking(itemPath, float(val))

            slider.valueChanged.connect(setFromSlider)
            spinBox.valueChanged.connect(setFromSpinBox)

            rowLayout.addWidget(slider, 1)
            rowLayout.addWidget(spinBox, 0)

            return container
    
        # fallback
        fallback = QLineEdit()
        fallback.setReadOnly(True)

        try:
            content = str(
                getByPath(self.workingConfig, itemPath)
            )

            fallback.setText(content)
        except Exception as e:
            fallback.setText(f"Error: {str(e)}")
        
        return fallback

    # state stuff
    def _setWorking(
        self,
        path: str,
        value: Any
    ) -> None:
        try:
            setByPath(self.workingConfig, path, value)
            self.dirty = True
        except Exception as _e:
            # TODO: add error handling
            pass

    def _previewLoadProfile(
        self,
        profileName: str
    ) -> None:
        overrides = readJSONFile(
            self.config.getProfilePath(profileName)
        )

        return deepMerge(
            self.config.defaultConfig,
            overrides
        )
    
    # profile controls
    def _onProfileSelected(self, profile: str) -> None:
        if not profile:
            return
        
        def continueProfileSwitch() -> None:
            self.selectedProfile = profile

            self.workingConfig = self._previewLoadProfile(profile)
            self.dirty = False

            self._rebuildTabs()

        if self.dirty:
            # TODO: prompt
            pass
        else:
            continueProfileSwitch()


