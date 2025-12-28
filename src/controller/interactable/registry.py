from PySide6.QtWidgets import QWidget, QDialog
from PySide6.QtGui import QIcon

from typing import Literal, Optional, Callable, Iterable
from dataclasses import dataclass

EntryKind = Literal["panel", "modal"]

@dataclass
class MenuEntry:
    id: str
    title: str
    kind: EntryKind
    icon: Optional[QIcon] = None

    panel_factory: Optional[Callable[[], QWidget]] = None
    modal_factory: Optional[Callable[[QWidget], QDialog]] = None

    singleton: bool = True

class PanelRegistry:
    def __init__(self):
        self.entries: dict[str, MenuEntry] = {}

    def registerEntry(self, entry: MenuEntry):
        if entry.id in self.entries:
            raise ValueError(f"Menu entry with ID '{entry.id}' is already registered.")
        
        if entry.kind == "panel" and entry.panel_factory is None:
            raise ValueError("Panel entries must have a panel_factory defined.")
        
        if entry.kind == "modal" and entry.modal_factory is None:
            raise ValueError("Modal entries must have a modal_factory defined.")

        self.entries[entry.id] = entry
    
    def getEntries(self) -> Iterable[MenuEntry]:
        return self.entries.values()
    
    def getEntry(self, entryID: str) -> Optional[MenuEntry]:
        return self.entries.get(entryID, None)
