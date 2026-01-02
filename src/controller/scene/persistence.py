from ..config import ConfigController
from ..asset import AssetController

from .model import DecorationEntity, SceneModel
from .layout import ScreenLayoutHandler, ScreenInfo

from PySide6.QtCore import QObject, QTimer, QPointF

from typing import Any, Dict, List, Optional
from copy import deepcopy

import random
import uuid

SAVE_INTERVAL_SEC = 60

class ScenePersistence(QObject):
    def __init__(
        self,
        model: SceneModel,
        config: Optional[ConfigController],
        layout: ScreenLayoutHandler,
        sprite: QObject = None
    ):
        super().__init__(sprite)

        self.model = model
        self.config = config
        self.layout = layout

        self.isLoading = False

        self._saveTimer = QTimer(self)
        self._saveTimer.setSingleShot(True)
        self._saveTimer.setInterval(SAVE_INTERVAL_SEC * 1000)
        self._saveTimer.timeout.connect(self.saveToConfig)

        self.assets = AssetController("images/decorations")

        self.model.entityAdded.connect(lambda _decorationEntity: self.scheduleSave())
        self.model.entityUpdated.connect(lambda _decorationEntity: self.scheduleSave())
        self.model.entityRemoved.connect(lambda _entityId: self.scheduleSave())
    
    def getStartupDecorationSpawnCount(self) -> int:
        if self.config is None:
            return 0
        
        return self.config.getValue("scene.startupDecorationSpawnCount")
    
    def getSavedDecorations(self) -> List[Dict[str, Any]]:
        if self.config is None:
            return []
        
        try:
            records = self.config.getValue("scene.persistentDecorations")
        except Exception:
            records = []

        if not isinstance(records, list):
            return []
        
        # filter out invalid records
        out = []

        for record in records:
            if not isinstance(record, dict):
                continue
            
            out.append(record)

        return out

    def setSavedDecorations(self, records: List[Dict[str, Any]]):
        if self.config is None:
            return
        
        self.config.setValue(
            "scene.persistentDecorations",
            deepcopy(records)
        )
    
    def loadOrSpawn(self) -> None:
        self.isLoading = True

        try:
            records = self.getSavedDecorations()

            if records:
                self.loadFromRecords(records)
            else:
                self.spawnDefaults()
        finally:
            self.isLoading = False
    
    def loadFromRecords(self, records: List[Dict[str, Any]]) -> None:
        for record in records:
            id = record.get("id", None)
            name = record.get("name", None)

            if (id is None) or (name is None):
                continue

            try:
                x = float(record.get("x", 0))
                y = float(record.get("y", 0))
            except Exception:
                x, y = 0.0, 0.0
            
            globalPosition = QPointF(x, y)

            newEntity = DecorationEntity(
                entityId=id,
                name=name,
                x=globalPosition.x(),
                y=globalPosition.y()
            )

            self.model.addEntity(newEntity)
    
    def spawnDefaults(self) -> None:
        decorationsList = [decoration.stem for decoration in self.assets.listDirectory()]

        if not decorationsList:
            return
        
        perScreen = max(0, self.getStartupDecorationSpawnCount())
        newRecords = []

        for screenInfo in self.layout.screens:
            bounds = screenInfo.boundsGlobal

            for _index in range(perScreen):
                name = random.choice(decorationsList)
                
                generatedX = random.uniform(
                    bounds.left(),
                    bounds.left() + max(1, bounds.width() - 32)
                )

                generatedY = random.uniform(
                    bounds.top(),
                    bounds.top() + max(1, bounds.height() - 32)
                )

                entityId = str(uuid.uuid4())
                newEntity = DecorationEntity(
                    entityId=entityId,
                    name=name,
                    x=generatedX,
                    y=generatedY
                )

                self.model.addEntity(newEntity)

                newRecords.append({
                    "id": entityId,
                    "name": name,
                    "x": generatedX,
                    "y": generatedY
                })
            
        self.setSavedDecorations(newRecords)
        self.scheduleSave()

    def scheduleSave(self) -> None:
        if self.isLoading:
            return
        
        self._saveTimer.start()
        self._saveTimer.stop()

    def saveToConfig(self) -> None:
        if self.config is None:
            return
        
        if self.isLoading:
            return
        
        try:
            records = []

            for entity in self.model.entitesList.values():
                records.append({
                    "id": entity.entityId,
                    "name": entity.name,
                    "x": entity.x,
                    "y": entity.y
                })
            
            self.setSavedDecorations(records)
            self.config.saveConfig()
        except Exception:
            pass