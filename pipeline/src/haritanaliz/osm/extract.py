"""Read administrative boundaries, place points and special-zone candidates from the OSM extract.

pyosmium (libosmium) assembles boundary and multipolygon relations into areas; the same code
runs on Windows and Linux (see docs/decisions.md). Everything is extracted with all its tags,
so that admin levels and unit types can be decided from the data instead of being assumed.

Outputs (GeoParquet, EPSG:4326) in ``out_dir``:
- ``areas.parquet``: polygons with boundary=administrative, a place tag, landuse=industrial
  (named only) or boundary=special_economic_zone.
- ``place_nodes.parquet``: place points (villages, neighbourhoods, ...).
- ``admin_relations.parquet``: every boundary=administrative relation with its label and
  admin_centre members, including relations libosmium could not assemble into a polygon.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import geopandas as gpd
import osmium
import pandas as pd
import shapely

AREAS_FILE = "areas.parquet"
PLACE_NODES_FILE = "place_nodes.parquet"
ADMIN_RELATIONS_FILE = "admin_relations.parquet"

PLACE_POINT_VALUES = (
    "city",
    "town",
    "village",
    "hamlet",
    "suburb",
    "quarter",
    "neighbourhood",
    "isolated_dwelling",
    "locality",
)
PLACE_AREA_VALUES = ("city", "town", "village", "hamlet", "suburb", "quarter", "neighbourhood")
AREA_TAGS: tuple[tuple[str, str], ...] = (
    ("boundary", "administrative"),
    ("boundary", "special_economic_zone"),
    ("landuse", "industrial"),
    *(("place", value) for value in PLACE_AREA_VALUES),
)


@dataclass(frozen=True)
class OsmBoundaryExtract:
    areas: gpd.GeoDataFrame
    place_nodes: gpd.GeoDataFrame
    admin_relations: pd.DataFrame


def extract_boundaries(
    pbf_path: Path, progress: Callable[[str], None] | None = None
) -> OsmBoundaryExtract:
    """Read the PBF once (pyosmium makes two passes internally for relations)."""
    area_filter = osmium.filter.TagFilter(*AREA_TAGS)
    output_filter = osmium.filter.TagFilter(
        *AREA_TAGS, *(("place", value) for value in PLACE_POINT_VALUES)
    )
    processor = (
        osmium.FileProcessor(str(pbf_path))
        .with_locations("flex_mem")
        .with_areas(area_filter)
        .with_filter(output_filter)
    )
    factory = osmium.geom.WKBFactory()

    area_rows: list[dict[str, Any]] = []
    area_wkb: list[str] = []
    node_rows: list[dict[str, Any]] = []
    relation_rows: list[dict[str, Any]] = []
    failed_geometries = 0

    for count, obj in enumerate(processor, start=1):
        if progress and count % 200_000 == 0:
            progress(f"{count:,} objects read")
        if obj.is_area():
            tags = _tags(obj)
            if tags.get("landuse") == "industrial" and "name" not in tags:
                continue
            try:
                wkb = factory.create_multipolygon(obj)
            except RuntimeError:
                failed_geometries += 1
                continue
            area_rows.append(
                {
                    "osm_type": "way" if obj.from_way() else "relation",
                    "osm_id": obj.orig_id(),
                    **_common_columns(tags),
                    "tags": json.dumps(tags, ensure_ascii=False, sort_keys=True),
                }
            )
            area_wkb.append(wkb)
        elif obj.is_node():
            tags = _tags(obj)
            if tags.get("place") not in PLACE_POINT_VALUES or not obj.location.valid():
                continue
            node_rows.append(
                {
                    "osm_id": obj.id,
                    **_common_columns(tags),
                    "tags": json.dumps(tags, ensure_ascii=False, sort_keys=True),
                    "lon": obj.location.lon,
                    "lat": obj.location.lat,
                }
            )
        elif obj.is_relation():
            tags = _tags(obj)
            if tags.get("boundary") != "administrative":
                continue
            relation_rows.append(
                {
                    "osm_id": obj.id,
                    **_common_columns(tags),
                    "tags": json.dumps(tags, ensure_ascii=False, sort_keys=True),
                    "label_node": _member(obj, "label"),
                    "admin_centre_node": _member(obj, "admin_centre"),
                    "member_ways": sum(1 for m in obj.members if m.type == "w"),
                }
            )

    if progress:
        progress(
            f"done: {len(area_rows):,} areas, {len(node_rows):,} place nodes, "
            f"{len(relation_rows):,} admin relations, {failed_geometries} geometry failures"
        )

    areas = gpd.GeoDataFrame(
        area_rows,
        geometry=shapely.from_wkb([bytes.fromhex(wkb) for wkb in area_wkb]),
        crs="EPSG:4326",
    )
    nodes = pd.DataFrame(node_rows)
    place_nodes = gpd.GeoDataFrame(
        nodes.drop(columns=["lon", "lat"]),
        geometry=gpd.points_from_xy(nodes["lon"], nodes["lat"]),
        crs="EPSG:4326",
    )
    relations = pd.DataFrame(relation_rows)
    relations["assembled"] = relations["osm_id"].isin(
        areas.loc[areas["osm_type"] == "relation", "osm_id"]
    )
    return OsmBoundaryExtract(areas=areas, place_nodes=place_nodes, admin_relations=relations)


def write_extract(extract: OsmBoundaryExtract, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    extract.areas.to_parquet(out_dir / AREAS_FILE)
    extract.place_nodes.to_parquet(out_dir / PLACE_NODES_FILE)
    extract.admin_relations.to_parquet(out_dir / ADMIN_RELATIONS_FILE)


def read_extract(out_dir: Path) -> OsmBoundaryExtract:
    return OsmBoundaryExtract(
        areas=gpd.read_parquet(out_dir / AREAS_FILE),
        place_nodes=gpd.read_parquet(out_dir / PLACE_NODES_FILE),
        admin_relations=pd.read_parquet(out_dir / ADMIN_RELATIONS_FILE),
    )


def extract_is_cached(out_dir: Path) -> bool:
    return all(
        (out_dir / name).is_file() for name in (AREAS_FILE, PLACE_NODES_FILE, ADMIN_RELATIONS_FILE)
    )


def _tags(obj: Any) -> dict[str, str]:
    return {tag.k: tag.v for tag in obj.tags}


def _common_columns(tags: dict[str, str]) -> dict[str, str | None]:
    return {
        "name": tags.get("name"),
        "boundary": tags.get("boundary"),
        "admin_level": tags.get("admin_level"),
        "place": tags.get("place"),
        "landuse": tags.get("landuse"),
    }


def _member(relation: Any, role: str) -> int | None:
    for member in relation.members:
        if member.type == "n" and member.role == role:
            return int(member.ref)
    return None
