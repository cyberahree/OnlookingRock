from PySide6.QtCore import QObject, Signal, QPointF

from dataclasses import dataclass
from typing import Dict, Optional

MIN_POSITION_SHIFT = 0.01

@dataclass
class DecorationEntity:
    """
    data model for a decoration entity in the scene.
    """

    entityId: str
    name: str
    x: float
    y: float

    transient: bool = False

    @property
    def globalPosition(self) -> QPointF:
        """
        get the global position of the decoration.
        
        :return: the global position point
        :rtype: QPointF
        """

        return QPointF(self.x, self.y)
    
    def setPosition(
        self,
        position: QPointF
    ):
        """
        set the position of the decoration.
        
        :param position: the new global position
        :type position: QPointF
        """

        self.x = position.x()
        self.y = position.y()

class SceneModel(QObject):
    """
    manages the scene model with decoration entities.
    
    Emits signals for entity add, update, and remove events for UI synchronisation.
    """

    entityAdded = Signal(DecorationEntity)
    entityUpdated = Signal(DecorationEntity)
    entityRemoved = Signal(str) # entity id

    def __init__(self, sprite: Optional[QObject] = None):
        """
        initialise the scene model.
        
        :param sprite: optional parent widget
        """

        super().__init__(sprite)

        self.entitesList: Dict[str, DecorationEntity] = {}

    def getEntity(self, entityId: str) -> Optional[DecorationEntity]:
        """
        get a decoration entity by id.
        
        :param entityId: the entity id to retrieve
        :type entityId: str
        :return: the entity or None if not found
        :rtype: Optional[DecorationEntity]
        """

        return self.entitesList.get(entityId, None)
    
    def addEntity(self, entity: DecorationEntity, emit: bool = True):
        """
        add a decoration entity to the scene model.
        
        :param entity: the entity to add
        :type entity: DecorationEntity
        :param emit: whether to emit the entityAdded signal
        :type emit: bool
        """

        self.entitesList[entity.entityId] = entity
    
        if emit:
            self.entityAdded.emit(entity)

    def removeEntity(
        self,
        entityId: str,
        emit: bool = True
    ):
        """
        remove a decoration entity from the scene model.
        
        :param entityId: the entity id to remove
        :type entityId: str
        :param emit: whether to emit the entityRemoved signal
        :type emit: bool
        """

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
        """
        update a decoration entity's name and/or position.
        
        :param entityId: the entity id to update
        :type entityId: str
        :param name: optional new name for the entity
        :type name: Optional[str]
        :param position: optional new global position
        :type position: Optional[QPointF]
        :param emit: whether to emit the entityUpdated signal
        :type emit: bool
        """

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
