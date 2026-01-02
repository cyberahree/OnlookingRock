from .primitives import _RockWidgetMixin
from .dropdown import RockDropdown
from .typography import BodyLabel
from ..styling import PADDING

from PySide6.QtGui import QColor
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
    on_changed: Optional[Callable[[str], None]] = None,
    max_length: int = 32,
    parent: Optional[QWidget] = None,
) -> tuple[QWidget, QLineEdit]:
    row = QWidget(parent)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(PADDING // 2)

    name_label = BodyLabel(label, selectable=False)
    name_label.setFixedWidth(120)
    layout.addWidget(name_label, 0)

    text_edit = QLineEdit()
    text_edit.setMaxLength(max_length)
    layout.addWidget(text_edit, 1)

    if on_changed is not None:
        text_edit.textChanged.connect(on_changed)

    return row, text_edit

def buildDropdownRow(
    label: str,
    items: List[str],
    *,
    on_changed: Optional[Callable[[str], None]] = None,
    parent: Optional[QWidget] = None,
) -> tuple[QWidget, "RockDropdown"]:
    from .dropdown import RockDropdown

    row = QWidget(parent)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(PADDING // 2)

    name_label = BodyLabel(label, selectable=False)
    name_label.setFixedWidth(120)
    layout.addWidget(name_label, 0)

    dropdown = RockDropdown(items=items)
    layout.addWidget(dropdown, 1)

    if on_changed is not None:
        dropdown.currentTextChanged.connect(on_changed)

    return row, dropdown

def buildSliderRow(
    label: str,
    min_val: int = 0,
    max_val: int = 100,
    on_changed: Optional[Callable[[int], None]] = None,
    label_width: int = 74,
    value_label_width: int = 42,
    show_percentage: bool = False,
    parent: Optional[QWidget] = None,
) -> tuple[QWidget, QSlider, QLabel]:
    row = QWidget(parent)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(PADDING // 2)

    name_label = BodyLabel(label, selectable=False)
    name_label.setFixedWidth(label_width)
    layout.addWidget(name_label, 0)

    slider = QSlider(Qt.Horizontal)
    slider.setRange(min_val, max_val)
    slider.setSingleStep(1)
    slider.setPageStep(max(1, (max_val - min_val) // 20))
    slider.setTracking(True)
    layout.addWidget(slider, 1)

    value_label = BodyLabel("0%")
    value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    value_label.setFixedWidth(value_label_width)
    layout.addWidget(value_label, 0)

    def on_value_changed(v: int) -> None:
        if show_percentage:
            percentage = int(round((v - min_val) / (max_val - min_val) * 100)) if max_val > min_val else 0
            value_label.setText(f"{percentage}%")
        else:
            value_label.setText(str(v))

        if on_changed is not None:
            on_changed(v)

    slider.valueChanged.connect(on_value_changed)

    # Initialize label display to match initial slider value (without triggering callback)
    if show_percentage:
        percentage = int(round((min_val - min_val) / (max_val - min_val) * 100)) if max_val > min_val else 0
        value_label.setText(f"{percentage}%")
    else:
        value_label.setText(str(min_val))

    return row, slider, value_label

def buildSpinboxRow(
    label: str,
    min_val: int = 0,
    max_val: int = 100,
    step: int = 1,
    suffix: str = "",
    on_changed: Optional[Callable[[int], None]] = None,
    parent: Optional[QWidget] = None,
) -> tuple[QWidget, QSpinBox]:
    row = QWidget(parent)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(PADDING // 2)

    name_label = BodyLabel(label, selectable=False)
    name_label.setFixedWidth(120)
    layout.addWidget(name_label, 0)

    spinbox = QSpinBox()
    spinbox.setMinimum(min_val)
    spinbox.setMaximum(max_val)
    spinbox.setSingleStep(step)
    if suffix:
        spinbox.setSuffix(suffix)
    layout.addWidget(spinbox, 1)

    if on_changed is not None:
        spinbox.valueChanged.connect(on_changed)

    return row, spinbox

def buildScaleSliderRow(
    label: str,
    min_scale: float = 0.25,
    max_scale: float = 2.0,
    on_changed: Optional[Callable[[float], None]] = None,
    on_released: Optional[Callable[[float], None]] = None,
    parent: Optional[QWidget] = None,
) -> tuple[QWidget, QSlider, QLabel]:
    row = QWidget(parent)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(PADDING // 2)

    name_label = BodyLabel(label, selectable=False)
    name_label.setFixedWidth(74)
    layout.addWidget(name_label, 0)

    # Convert scale range to integer range (multiply by 100)
    slider_min = int(min_scale * 100)
    slider_max = int(max_scale * 100)

    slider = QSlider(Qt.Horizontal)
    slider.setRange(slider_min, slider_max)
    slider.setSingleStep(5)
    slider.setPageStep(10)
    slider.setTracking(True)
    layout.addWidget(slider, 1)

    value_label = BodyLabel(f"{min_scale:.2f}x")
    value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    value_label.setFixedWidth(42)
    layout.addWidget(value_label, 0)

    def on_value_changed(v: int) -> None:
        scale = v / 100.0
        value_label.setText(f"{scale:.2f}x")

        if on_changed is not None:
            on_changed(scale)

    def on_slider_released() -> None:
        scale = slider.value() / 100.0
        if on_released is not None:
            on_released(scale)

    slider.valueChanged.connect(on_value_changed)
    slider.sliderReleased.connect(on_slider_released)

    return row, slider, value_label
