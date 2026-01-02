from PySide6.QtCore import QPoint, QRect, QSize

from typing import Optional, Sequence
from dataclasses import dataclass

@dataclass
class AnchorSpec:
    """
    specification for anchor points with preferred and alternate positions
    """

    preferredPoint: QPoint
    """the preferred anchor point"""

    alternatePoint: QPoint
    """the alternate anchor point if preferred is not available"""

def computeIntersectingArea(boundA: QRect, boundB: QRect) -> int:
    """
    Compute the intersecting area between two rectangles.

    :param boundA: First rectangle
    :type boundA: QRect
    :param boundB: Second rectangle
    :type boundB: QRect
    :return: Area of intersection in pixels
    :rtype: int
    """
    intersection = boundA.intersected(boundB)

    if intersection.isNull():
        return 0

    return max(0, intersection.width()) * max(0, intersection.height())

def clampToScreen(position: QPoint, size: QSize, screen: QRect, margin: int = 0) -> QPoint:
    """
    Clamp a position and size to remain within screen bounds with margin.

    :param position: The position to clamp
    :type position: QPoint
    :param size: The size of the element
    :type size: QSize
    :param screen: The screen bounds
    :type screen: QRect
    :param margin: Margin from screen edges, defaults to 0
    :type margin: int
    :return: The clamped position
    :rtype: QPoint
    """
    x = max(
        screen.left() + margin,
        min(position.x(), screen.right() - size.width() - margin),
    )

    y = max(
        screen.top() + margin,
        min(position.y(), screen.bottom() - size.height() - margin),
    )

    return QPoint(x, y)

def score(bounds: QRect, preferredTopLeft: QPoint, occluders: Sequence[QRect]) -> tuple[int, int]:
    """
    Calculate a score for a position based on overlap and distance from preferred point.

    :param bounds: The rectangle bounds to score
    :type bounds: QRect
    :param preferredTopLeft: The preferred top-left position
    :type preferredTopLeft: QPoint
    :param occluders: Sequence of occluding rectangles
    :type occluders: Sequence[QRect]
    :return: Tuple of (overlap_area, manhattan_distance) for scoring
    :rtype: tuple[int, int]
    """
    overlap = sum(computeIntersectingArea(bounds, occluder) for occluder in occluders)
    distance = (bounds.topLeft() - preferredTopLeft).manhattanLength()
    return (overlap, distance)

def bestCandidate(
    preferredPoint: QPoint,
    alternatePoint: QPoint,
    size: QSize,
    screen: QRect,
    occluders: Sequence[QRect],
    margin: int = 0,
) -> QPoint:
    """
    Find the best candidate position that minimizes overlap with occluders.

    :param preferredPoint: The preferred anchor point
    :type preferredPoint: QPoint
    :param alternatePoint: The alternate anchor point
    :type alternatePoint: QPoint
    :param size: Size of the element being positioned
    :type size: QSize
    :param screen: The screen bounds to contain the element
    :type screen: QRect
    :param occluders: Sequence of occluding rectangles to avoid
    :type occluders: Sequence[QRect]
    :param margin: Margin from screen edges, defaults to 0
    :type margin: int
    :return: The best candidate position
    :rtype: QPoint
    """
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
