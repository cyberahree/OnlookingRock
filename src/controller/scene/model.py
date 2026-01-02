from PySide6.QtCore import QObject, Signal, QPointF

from typing import Dict, Iterable, Optional
from dataclasses import dataclass

MIN_POSITION_SHIFT = 0.01

@dataclass
class DecorationEntity:
    entityId: str
    name: str
    x: float
    y: float

    @property
    def globalPosition(self) -> QPointF:
        return QPointF(self.x, self.y)
    
    def setPosition(
        self,
        position: QPointF
    ):
        self.x = position.x()
        self.y = position.y()

class SceneModel(QObject):
    entityAdded = Signal(DecorationEntity)
    entityUpdated = Signal(DecorationEntity)
    entityRemoved = Signal(str) # entity id

    def __init__(self, sprite = None):
        super().__init__(sprite)

        self.entitesList: Dict[str, DecorationEntity] = {}

    def getEntity(self, entityId: str) -> Optional[DecorationEntity]:
        return self.entitesList.get(entityId, None)
    
    def addEntity(self, entity: DecorationEntity, emit: bool = True):
        self.entitesList[entity.entityId] = entity
    
        if emit:
            self.entityAdded.emit(entity)

    def removeEntity(
        self,
        entityId: str,
        emit: bool = True
    ):
        if entityId not in self.entitesList:
            return
        
        del self.entitesList[entityId]

        if emit:
            self.entityRemoved.emit(entityId)
    
    def updateEntity(
        self,
        entityId: str,
        name: Optional[str] = None,
        position: Optional[QPointF] = None,
        emit: bool = True
    ):
        entity = self.getEntity(entityId)
        changed = False

        if entity is None:
            return
        
        if (name is not None) and (entity.name != name):
            entity.name = name
            changed = True
        
        if (position is not None):
            newX = float(position.x())
            newY = float(position.y())

            insignificantShift = (
                abs(entity.x - newX) < MIN_POSITION_SHIFT and
                abs(entity.y - newY) < MIN_POSITION_SHIFT
            )

            if not insignificantShift:
                entity.setPosition(position)
                changed = True

        if changed and emit:
            self.entityUpdated.emit(entity)