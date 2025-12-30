from ..styling import (
    ACTION_ACCENT,
    BACKGROUND_COLOR,
    BORDER_COLOR,
    BORDER_RADIUS,
    ERROR_ACCENT,
    INFO_ACCENT,
    TEXT_COLOR,
    asRGB,
)

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QColor

from typing import Optional

_CACHED_QSS: Optional[str] = None

def _rgba(color: QColor, alpha: Optional[int] = None) -> str:
    if alpha is None:
        return asRGB(color)

    c = QColor(color)
    c.setAlpha(int(max(0, min(255, alpha))))
    return asRGB(c)

def _build_base_qss() -> str:
    hover_surface = QColor(BACKGROUND_COLOR).darker(106)
    pressed_surface = QColor(BACKGROUND_COLOR).darker(112)

    primary_fill = QColor(ACTION_ACCENT)
    primary_hover = QColor(ACTION_ACCENT).lighter(112)
    primary_pressed = QColor(ACTION_ACCENT).darker(112)

    info_fill = QColor(INFO_ACCENT)
    info_hover = QColor(INFO_ACCENT).lighter(112)
    info_pressed = QColor(INFO_ACCENT).darker(112)

    danger_fill = QColor(ERROR_ACCENT)
    danger_hover = QColor(ERROR_ACCENT).lighter(112)
    danger_pressed = QColor(ERROR_ACCENT).darker(112)

    return f"""
    QFrame[rockRole=\"container\"] {{
        background-color: {_rgba(BACKGROUND_COLOR)};
        border: 1px solid {_rgba(BORDER_COLOR)};
        border-radius: {BORDER_RADIUS}px;
    }}

    QFrame[rockRole=\"container\"][variant=\"surface\"] {{
        border: none;
    }}

    QFrame[rockRole=\"container\"][variant=\"card\"] {{
        border: 1px solid {_rgba(BORDER_COLOR)};
    }}

    QFrame[rockRole=\"container\"][variant=\"inset\"] {{
        background-color: {_rgba(QColor(BACKGROUND_COLOR).darker(104))};
        border: 1px solid {_rgba(QColor(BORDER_COLOR).darker(106))};
    }}

    QFrame[rockRole=\"container\"][variant=\"ghost\"] {{
        background: transparent;
        border: none;
    }}

    QLabel[rockRole=\"heading\"],
    QLabel[rockRole=\"subheading\"],
    QLabel[rockRole=\"text\"],
    QLabel[rockRole=\"muted\"] {{
        color: {_rgba(TEXT_COLOR)};
    }}

    QLabel[rockRole=\"muted\"] {{
        color: rgba({TEXT_COLOR.red()}, {TEXT_COLOR.green()}, {TEXT_COLOR.blue()}, 170);
    }}

    QPushButton[rockRole=\"button\"] {{
        color: {_rgba(TEXT_COLOR)};
        background-color: rgba(255, 255, 255, 120);
        border: 1px solid rgba(0, 0, 0, 35);
        border-radius: {BORDER_RADIUS}px;
        padding: 4px 10px;
        outline: none;
    }}

    QPushButton[rockRole=\"button\"]:hover {{
        background-color: rgba(255, 255, 255, 180);
    }}

    QPushButton[rockRole=\"button\"]:pressed {{
        background-color: rgba(0, 0, 0, 18);
    }}

    QPushButton[rockRole=\"button\"][variant=\"ghost\"] {{
        background: transparent;
        border: none;
        padding: 2px 6px;
    }}

    QPushButton[rockRole=\"button\"][variant=\"ghost\"]:hover {{
        background-color: rgba(0, 0, 0, 18);
    }}

    QPushButton[rockRole=\"button\"][variant=\"ghost\"]:pressed {{
        background-color: rgba(0, 0, 0, 28);
    }}

    QPushButton[rockRole=\"button\"][variant=\"surface\"] {{
        background-color: {_rgba(BACKGROUND_COLOR)};
        border: 1px solid {_rgba(BORDER_COLOR)};
    }}

    QPushButton[rockRole=\"button\"][variant=\"surface\"]:hover {{
        background-color: {_rgba(hover_surface)};
    }}

    QPushButton[rockRole=\"button\"][variant=\"surface\"]:pressed {{
        background-color: {_rgba(pressed_surface)};
    }}

    QPushButton[rockRole=\"button\"][variant=\"primary\"] {{
        background-color: {_rgba(primary_fill, 230)};
        border: 1px solid {_rgba(primary_fill.darker(120))};
    }}

    QPushButton[rockRole=\"button\"][variant=\"primary\"]:hover {{
        background-color: {_rgba(primary_hover, 235)};
    }}

    QPushButton[rockRole=\"button\"][variant=\"primary\"]:pressed {{
        background-color: {_rgba(primary_pressed, 235)};
    }}

    QPushButton[rockRole=\"button\"][variant=\"info\"] {{
        background-color: {_rgba(info_fill, 230)};
        border: 1px solid {_rgba(info_fill.darker(120))};
    }}

    QPushButton[rockRole=\"button\"][variant=\"info\"]:hover {{
        background-color: {_rgba(info_hover, 235)};
    }}

    QPushButton[rockRole=\"button\"][variant=\"info\"]:pressed {{
        background-color: {_rgba(info_pressed, 235)};
    }}

    QPushButton[rockRole=\"button\"][variant=\"danger\"] {{
        background-color: {_rgba(danger_fill, 225)};
        border: 1px solid {_rgba(danger_fill.darker(120))};
    }}

    QPushButton[rockRole=\"button\"][variant=\"danger\"]:hover {{
        background-color: {_rgba(danger_hover, 235)};
    }}

    QPushButton[rockRole=\"button\"][variant=\"danger\"]:pressed {{
        background-color: {_rgba(danger_pressed, 235)};
    }}

    QFrame[rockRole=\"divider\"] {{
        background-color: rgba(0, 0, 0, 35);
        min-height: 1px;
        max-height: 1px;
    }}
    """.strip()

def rockStylesheet() -> str:
    global _CACHED_QSS

    if _CACHED_QSS is None:
        _CACHED_QSS = _build_base_qss()

    return _CACHED_QSS

def applyRockStyle(root: QWidget, extraQss: str = "") -> None:
    base = rockStylesheet()

    if extraQss:
        root.setStyleSheet(base + "\n\n" + extraQss)
    else:
        root.setStyleSheet(base)
