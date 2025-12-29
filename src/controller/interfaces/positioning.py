from PySide6.QtCore import QPoint, QRect, QSize

from typing import Sequence, Optional
from dataclasses import dataclass

@dataclass
class AnchorSpec:
    preferredPoint: QPoint
    alternatePoint: QPoint

def computeIntersectingArea(
    boundA: QRect,
    boundB: QRect
) -> int:
    intersection = boundA.intersected(boundB)

    if intersection.isNull():
        return 0

    return max(0, intersection.width()) * max(0, intersection.height())

def clampToScreen(
    position: QPoint,
    size: QSize,
    screen: QRect,
    margin: int = 0
) -> QPoint:
    x = max(
        screen.left() + margin,
        min(position.x(),screen.right() - size.width() - margin)
    )

    y = max(
        screen.top() + margin,
        min(position.y(), screen.bottom() - size.height() - margin)
    )

    return QPoint(x, y)

def score(
    bounds: QRect,
    preferredTopLeft: QPoint,
    occluders: Sequence[QRect]
) -> tuple[int, int]:
    overlap = sum(
        computeIntersectingArea(bounds, occluder) for occluder in occluders
    )

    distance = (bounds.topLeft() - preferredTopLeft).manhattanLength()
    return (overlap, distance)

def bestCandidate(
    preferredPoint: QPoint,
    alternatePoint: QPoint,
    size: QSize,
    screen: QRect,
    occluders: Sequence[QRect],
    margin: int = 0
) -> QPoint:
    candidates: list[QPoint] = []

    def addBaseplusNudges(base: QPoint) -> None:
        candidates.append(base)
        baseRectangle = QRect(base, size)

        for occluder in occluders:
            if not baseRectangle.intersects(occluder):
                continue
                
            candidates.append(QPoint(base.x(), occluder.top() - size.height() - margin))
            candidates.append(QPoint(base.x(), occluder.bottom() + margin))
    
    addBaseplusNudges(preferredPoint)
    addBaseplusNudges(alternatePoint)

    bestPoint: Optional[QPoint] = None
    bestScore: Optional[tuple[int, int]] = None

    for point in candidates:
        clampedPoint = clampToScreen(point, size, screen, margin)
        bounds = QRect(clampedPoint, size)

        candidateScore = score(bounds, preferredPoint, occluders)

        if bestScore is None or candidateScore < bestScore:
            bestScore = candidateScore
            bestPoint = clampedPoint

            if candidateScore[0] == 0:
                break

    return bestPoint or preferredPoint
