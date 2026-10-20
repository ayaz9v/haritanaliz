"""Geometry repair and area helpers."""

from __future__ import annotations

import numpy as np
import shapely
from shapely.geometry.base import BaseGeometry

POLYGONAL = ("Polygon", "MultiPolygon")


def polygonal_part(geom: BaseGeometry | None) -> BaseGeometry | None:
    """Only the polygons of a geometry (make_valid may return lines or points as well)."""
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type in POLYGONAL:
        return geom
    parts = [part for part in shapely.get_parts(geom) if part.geom_type in POLYGONAL]
    if not parts:
        return None
    return shapely.union_all(parts)


def repair(geoms: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Make geometries valid and polygonal.

    Self-intersections and other errors are fixed with GEOS make_valid ("structure" method,
    which keeps the area enclosed by the rings). Returns the repaired geometries (``None``
    where nothing polygonal remains) and a mask of the ones that were invalid.
    """
    geoms = np.asarray(geoms, dtype=object)
    invalid = ~shapely.is_valid(geoms)
    fixed = geoms.copy()
    if invalid.any():
        fixed[invalid] = shapely.make_valid(
            geoms[invalid], method="structure", keep_collapsed=False
        )
    result = np.array([polygonal_part(geom) for geom in fixed], dtype=object)
    return result, invalid


def remove_slivers(
    geom: BaseGeometry | None, width_m: float, min_area_m2: float
) -> BaseGeometry | None:
    """Drop thin slivers (narrower than ``width_m``) and parts smaller than ``min_area_m2``.

    Used on gaps between neighbouring polygons, where tiny mismatches of shared borders
    would otherwise count as uncovered land. Coordinates must be in metres.
    """
    if geom is None or geom.is_empty:
        return None
    # Mitre joins keep corners sharp, so an opening does not shave area off normal polygons.
    opened = shapely.buffer(
        shapely.buffer(geom, -width_m / 2, join_style="mitre"), width_m / 2, join_style="mitre"
    )
    cleaned = shapely.intersection(opened, geom)
    parts = [
        part
        for part in shapely.get_parts(polygonal_part(cleaned) or shapely.Polygon())
        if part.area >= min_area_m2
    ]
    return shapely.union_all(parts) if parts else None
