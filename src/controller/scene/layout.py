from PySide6.QtGui import QGuiApplication, QScreen
from PySide6.QtCore import QPoint, QRect

from dataclasses import dataclass
from typing import Optional

@dataclass
class ScreenInfo:
    name: str
    boundsGlobal: QRect

def getScreenName(screen: QScreen) -> str:
    return getattr(screen, 'name', lambda: '')()

class ScreenLayoutHandler:
    """
    manages screen layout information for multi-monitor setups.
    """

    def __init__(self):
        """
        initialise the screen layout handler and refresh screen info.
        """

        self.screens: list[ScreenInfo] = []
        self.refresh()
    
    def refresh(self):
        """
        refresh the screen layout information from the system.
        """

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
        """
        get the primary screen information.
        
        :return: the primary screen info
        :rtype: ScreenInfo
        """

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
        """
        get screen information by name.
        
        :param name: the screen name to look up
        :type name: str
        :return: the screen info or None if not found
        :rtype: Optional[ScreenInfo]
        """

        for info in self.screens:
            if info.name != name:
                continue

            return info
        
        return None

    def getScreenAtPoint(
        self,
        pointGlobal: QPoint
    ) -> Optional[ScreenInfo]:
        """
        get the screen containing a global point.
        
        :param pointGlobal: the global point to check
        :type pointGlobal: QPoint
        :return: the screen info containing the point or None
        :rtype: Optional[ScreenInfo]
        """

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
        """
        get the bounding rectangle for a screen by name.
        
        :param name: the screen name
        :type name: str
        :return: the screen bounds or None if not found
        :rtype: Optional[QRect]
        """

        screenInfo = self.getByName(name)

        if screenInfo is not None:
            return screenInfo.boundsGlobal
        
        return None
    
    def freshQueryForScreen(self, name: str) -> Optional[QScreen]:
        """
        query the system for a screen by name.
        
        :param name: the screen name to query
        :type name: str
        :return: the QScreen object or None if not found
        :rtype: Optional[QScreen]
        """

        for screen in QGuiApplication.screens():
            screenName = getScreenName(screen)

            if screenName != name:
                continue

            return screen
        
        return None

