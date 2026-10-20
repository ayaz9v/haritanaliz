"""Approximate boundaries for neighbourhoods/villages that exist in OSM only as points.

Inside a district, the land not covered by any boundary polygon (the gap) is split among the
place points that lie in it with a Voronoi diagram: every location goes to the nearest point.
Each connected part of the gap is handled on its own, so a cell never jumps across a mapped
polygon. Parts without points stay uncovered and are reported.
"""

from __future__ import annotations

from collections.abc import Sequence

import shapely
from shapely.geometry.base import BaseGeometry

from haritanaliz.boundaries.geometry import polygonal_part


def voronoi_cells(
    points: Sequence[shapely.Point], region: BaseGeometry
) -> list[BaseGeometry | None]:
    """Voronoi cells of distinct ``points``, clipped to ``region``, in the order of the points."""
    if not points:
        return []
    if len(points) == 1:
        return [region]
    diagram = shapely.voronoi_polygons(
        shapely.MultiPoint(list(points)), extend_to=region, ordered=True
    )
    cells = list(shapely.get_parts(diagram))
    if len(cells) != len(points):
        raise ValueError("points must be distinct")
    return [polygonal_part(shapely.intersection(cell, region)) for cell in cells]


def split_gap(gap: BaseGeometry | None, points: Sequence[shapely.Point]) -> dict[int, BaseGeometry]:
    """Split ``gap`` among ``points`` (by position in the sequence).

    Points outside the gap get nothing. Duplicate coordinates: only the first point is used.
    Returns {point position: geometry} for points that received an area.
    """
    if gap is None or gap.is_empty or not points:
        return {}
    first_at: dict[tuple[float, float], int] = {}
    for position, point in enumerate(points):
        first_at.setdefault((point.x, point.y), position)
    usable = sorted(first_at.values())

    result: dict[int, BaseGeometry] = {}
    for part in shapely.get_parts(gap):
        inside = [p for p in usable if part.covers(points[p])]
        if not inside:
            continue
        for position, cell in zip(
            inside, voronoi_cells([points[p] for p in inside], part), strict=True
        ):
            if cell is not None and not cell.is_empty:
                result[position] = cell
    return result
