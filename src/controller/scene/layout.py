from PySide6.QtGui import QGuiApplication, QScreen
from PySide6.QtCore import QPoint, QRect

from typing import Iterable, Optional
from dataclasses import dataclass

@dataclass
class ScreenInfo:
    name: str
    boundsGlobal: QRect

def getScreenName(screen: QScreen) -> str:
    return getattr(screen, 'name', lambda: '')()

class ScreenLayoutHandler:
    def __init__(self):
        self.screens: list[ScreenInfo] = []
        self.refresh()
    
    def refresh(self):
        self.screens.clear()

        for screen in QGuiApplication.screens():
            name = getattr(screen, 'name', lambda: '')()
            bounds = screen.geometry()

            self.screens.append(ScreenInfo(
                name=name,
                boundsGlobal=bounds
            ))

    @property
    def primary(self) -> ScreenInfo:
        primaryScreen = QGuiApplication.primaryScreen()

        if primaryScreen is not None:
            primaryScreenName = getScreenName(primaryScreen)
            identifiedScreen = self.getByName(primaryScreenName)

            if identifiedScreen is not None:
                return identifiedScreen

        return self.screens[0] if self.screens else None

    def getByName(
        self,
        name: str
    ) -> Optional[ScreenInfo]:
        for info in self.screens:
            if info.name != name:
                continue

            return info
        
        return None

    def getScreenAtPoint(
        self,
        pointGlobal: QPoint
    ) -> Optional[ScreenInfo]:
        try:
            detectedScreen = QGuiApplication.screenAt(pointGlobal)
        except Exception:
            detectedScreen = None
        
        # get by name
        if detectedScreen is not None:
            detectedScreenName = getScreenName(detectedScreen)
            identifiedScreen = self.getByName(detectedScreenName)

            if identifiedScreen is not None:
                return identifiedScreen
        
        # fallback to bounds check
        for info in self.screens:
            if not info.boundsGlobal.contains(pointGlobal):
                continue

            return info
        
        return None
    
    def getBoundForScreen(self, name: str) -> Optional[QRect]:
        screenInfo = self.getByName(name)

        if screenInfo is not None:
            return screenInfo.boundsGlobal
        
        return None
    
    def freshQueryForScreen(self, name: str) -> Optional[QScreen]:
        for screen in QGuiApplication.screens():
            screenName = getScreenName(screen)

            if screenName != name:
                continue

            return screen
        
        return None