from .dropdown import RockDropdown
from .typography import BodyLabel
from .switch import ToggleSwitch
from ..styling import PADDING

from PySide6.QtCore import Qt

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QSlider,
    QSpinBox,
    QWidget,
    QLabel,
)

from typing import Callable, List, Optional

def buildTextInputRow(
    label: str,
    onChanged: Optional[Callable[[str], None]] = None,
    max_length: int = 32,
    parent: Optional[QWidget] = None,
) -> tuple[QWidget, QLineEdit]:
    row = QWidget(parent)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(PADDING // 2)

    nameLabel = BodyLabel(label, selectable=False)
    nameLabel.setFixedWidth(120)
    layout.addWidget(nameLabel, 0)

    textEdit = QLineEdit()
    textEdit.setMaxLength(max_length)
    layout.addWidget(textEdit, 1)

    if onChanged is not None:
        textEdit.textChanged.connect(onChanged)

    return row, textEdit

def buildDropdownRow(
    label: str,
    items: List[str],
    onChanged: Optional[Callable[[str], None]] = None,
    parent: Optional[QWidget] = None,
) -> tuple[QWidget, "RockDropdown"]:
    from .dropdown import RockDropdown

    row = QWidget(parent)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(PADDING // 2)

    nameLabel = BodyLabel(label, selectable=False)
    nameLabel.setFixedWidth(120)
    layout.addWidget(nameLabel, 0)

    dropdown = RockDropdown(items=items)
    layout.addWidget(dropdown, 1)

    if onChanged is not None:
        dropdown.currentTextChanged.connect(onChanged)

    return row, dropdown

def buildSliderRow(
    label: str,
    min_val: int = 0,
    max_val: int = 100,
    onChanged: Optional[Callable[[int], None]] = None,
    labelWidth: int = 74,
    valueLabelWidth: int = 42,
    showPercentage: bool = False,
    parent: Optional[QWidget] = None,
) -> tuple[QWidget, QSlider, QLabel]:
    row = QWidget(parent)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(PADDING // 2)

    nameLabel = BodyLabel(label, selectable=False)
    nameLabel.setFixedWidth(labelWidth)
    layout.addWidget(nameLabel, 0)

    slider = QSlider(Qt.Horizontal)
    slider.setRange(min_val, max_val)
    slider.setSingleStep(1)
    slider.setPageStep(max(1, (max_val - min_val) // 20))
    slider.setTracking(True)
    layout.addWidget(slider, 1)

    valueLabel = BodyLabel("0%")
    valueLabel.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    valueLabel.setFixedWidth(valueLabelWidth)
    layout.addWidget(valueLabel, 0)

    def onValueChanged(v: int) -> None:
        if showPercentage:
            percentage = int(round((v - min_val) / (max_val - min_val) * 100)) if max_val > min_val else 0
            valueLabel.setText(f"{percentage}%")
        else:
            valueLabel.setText(str(v))

        if onChanged is not None:
            onChanged(v)

    slider.valueChanged.connect(onValueChanged)

    if showPercentage:
        percentage = int(round((min_val - min_val) / (max_val - min_val) * 100)) if max_val > min_val else 0
        valueLabel.setText(f"{percentage}%")
    else:
        valueLabel.setText(str(min_val))

    return row, slider, valueLabel

def buildSpinboxRow(
    label: str,
    minValue: int = 0,
    maxValue: int = 100,
    step: int = 1,
    suffix: str = "",
    onChanged: Optional[Callable[[int], None]] = None,
    parent: Optional[QWidget] = None,
) -> tuple[QWidget, QSpinBox]:
    row = QWidget(parent)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(PADDING // 2)

    nameLabel = BodyLabel(label, selectable=False)
    nameLabel.setFixedWidth(120)
    layout.addWidget(nameLabel, 0)

    spinbox = QSpinBox()
    spinbox.setMinimum(minValue)
    spinbox.setMaximum(maxValue)
    spinbox.setSingleStep(step)

    if suffix:
        spinbox.setSuffix(suffix)

    layout.addWidget(spinbox, 1)

    if onChanged is not None:
        spinbox.valueChanged.connect(onChanged)

    return row, spinbox

def buildScaleSliderRow(
    label: str,
    minScale: float = 0.25,
    maxScale: float = 2.0,
    onChanged: Optional[Callable[[float], None]] = None,
    onReleased: Optional[Callable[[float], None]] = None,
    parent: Optional[QWidget] = None,
) -> tuple[QWidget, QSlider, QLabel]:
    row = QWidget(parent)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(PADDING // 2)

    nameLabel = BodyLabel(label, selectable=False)
    nameLabel.setFixedWidth(74)
    layout.addWidget(nameLabel, 0)

    sliderMin = int(minScale * 100)
    sliderMax = int(maxScale * 100)

    slider = QSlider(Qt.Horizontal)
    slider.setRange(sliderMin, sliderMax)
    slider.setSingleStep(5)
    slider.setPageStep(10)
    slider.setTracking(True)
    layout.addWidget(slider, 1)

    valueLabel = BodyLabel(f"{minScale:.2f}x")
    valueLabel.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    valueLabel.setFixedWidth(42)
    layout.addWidget(valueLabel, 0)

    def onValueChanged(v: int) -> None:
        scale = v / 100.0
        valueLabel.setText(f"{scale:.2f}x")

        if onChanged is not None:
            onChanged(scale)

    def onSliderReleased() -> None:
        scale = slider.value() / 100.0

        if onReleased is not None:
            onReleased(scale)

    slider.valueChanged.connect(onValueChanged)
    slider.sliderReleased.connect(onSliderReleased)

    return row, slider, valueLabel

def buildSwitchRow(
    label: str,
    onChanged: Optional[Callable[[bool], None]] = None,
    parent: Optional[QWidget] = None,
) -> tuple[QWidget, ToggleSwitch]:
    """
    build a row with a label and toggle switch.
    
    :param label: the label text to display
    :type label: str
    :param onChanged: callback when switch state changes
    :type onChanged: Optional[Callable[[bool], None]]
    :param parent: parent widget
    :type parent: Optional[QWidget]
    :return: tuple of (row widget, toggle switch)
    :rtype: tuple[QWidget, ToggleSwitch]
    """
    row = QWidget(parent)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(PADDING // 2)

    nameLabel = BodyLabel(label, selectable=False)
    nameLabel.setFixedWidth(120)
    layout.addWidget(nameLabel, 0)

    switch = ToggleSwitch(onChanged=onChanged)
    layout.addWidget(switch, 0, Qt.AlignLeft)
    
    stateLabel = BodyLabel("disabled", selectable=False)
    stateLabel.setFixedWidth(64)
    layout.addWidget(stateLabel, 0, Qt.AlignLeft)
    
    def onSwitchChanged(checked: bool):
        stateLabel.setText("enabled" if checked else "disabled")

        if onChanged is not None:
            onChanged(checked)
    
    switch._onChanged = onSwitchChanged
    stateLabel.setText("enabled" if switch.isChecked() else "disabled")
    
    layout.addStretch(1)

    return row, switch, stateLabel
