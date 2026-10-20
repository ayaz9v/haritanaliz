"""Web outputs of the boundary build: region lists for search/selection and tile input.

Files in a data version (see docs/architecture.md, "Veri sözleşmesi"):
- ``regions/index.json``: all provinces and districts; loaded when the site opens.
- ``regions/<province id>.json``: neighbourhoods/villages of one province; loaded on demand.
- ``regions/search.json``: compact list of every neighbourhood/village for the search box;
  loaded on the first search.
Tile input (GeoJSONSeq for tippecanoe) is written next to the interim data, not published.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import geopandas as gpd
import shapely
from shapely.ops import polylabel

from haritanaliz.boundaries.build import BoundaryBuild
from haritanaliz.config import TileSettings
from haritanaliz.text import tr_sort_key

SCHEMA_VERSION = 1
LICENSE = "ODbL-1.0"
ATTRIBUTION = "© OpenStreetMap katkıcıları"
REGIONS_DIR = "regions"
INDEX_FILE = f"{REGIONS_DIR}/index.json"
SEARCH_FILE = f"{REGIONS_DIR}/search.json"
COORD_PRECISION = 1e-6  # degrees, about 0.1 m


def bbox(geom: Any) -> list[float]:
    return [round(value, 5) for value in geom.bounds]


def chunk_path(province_id: str) -> str:
    return f"{REGIONS_DIR}/{province_id}.json"


def region_index(build: BoundaryBuild) -> dict[str, Any]:
    """Provinces and districts. ``chunk`` is null for provinces without unit data (samples)."""
    with_units = set(build.units["province_id"])
    provinces = build.provinces.sort_values("name", key=lambda s: s.map(tr_sort_key))
    districts = build.districts.dropna(subset=["province_id"])
    districts = districts.sort_values(
        ["province_id", "name"], key=lambda s: s.map(tr_sort_key) if s.name == "name" else s
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "license": LICENSE,
        "attribution": ATTRIBUTION,
        "provinces": [
            {
                "id": row.id,
                "name": row.name,
                "code": row.code,
                "bbox": bbox(row.geometry),
                "area_km2": round(row.area_km2, 3),
                "chunk": chunk_path(row.id) if row.id in with_units else None,
            }
            for row in provinces.itertuples()
        ],
        "districts": [
            {
                "id": row.id,
                "name": row.name,
                "province": row.province_id,
                "bbox": bbox(row.geometry),
                "area_km2": round(row.area_km2, 3),
            }
            for row in districts.itertuples()
        ],
    }


def province_chunk(units: gpd.GeoDataFrame, province_id: str) -> dict[str, Any]:
    ordered = units.sort_values(
        ["district_id", "name"], key=lambda s: s.map(tr_sort_key) if s.name == "name" else s
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "license": LICENSE,
        "attribution": ATTRIBUTION,
        "province": province_id,
        "units": [
            {
                "id": row.id,
                "name": row.name,
                "type": row.type,
                "district": row.district_id,
                "bbox": bbox(row.geometry),
                "area_km2": round(row.area_km2, 3),
                "approx": bool(row.approx),
            }
            for row in ordered.itertuples()
        ],
    }


def search_index(build: BoundaryBuild) -> dict[str, Any]:
    """Every unit as [name, type, district position, id]; districts listed once."""
    district_ids = sorted(build.units["district_id"].unique())
    position = {district_id: i for i, district_id in enumerate(district_ids)}
    units = build.units.sort_values("name", key=lambda s: s.map(tr_sort_key))
    return {
        "schema_version": SCHEMA_VERSION,
        "license": LICENSE,
        "attribution": ATTRIBUTION,
        "districts": district_ids,
        "units": [
            [row.name, row.type, position[row.district_id], row.id] for row in units.itertuples()
        ],
    }


def write_regions(build: BoundaryBuild, version_dir: Path) -> dict[str, str]:
    """Write the region files; returns the manifest file entries."""
    (version_dir / REGIONS_DIR).mkdir(parents=True, exist_ok=True)
    _write_json(version_dir / INDEX_FILE, region_index(build))
    for province_id, units in build.units.groupby("province_id"):
        _write_json(version_dir / chunk_path(province_id), province_chunk(units, province_id))
    _write_json(version_dir / SEARCH_FILE, search_index(build))
    return {"regions": INDEX_FILE, "region_search": SEARCH_FILE}


def write_tile_input(build: BoundaryBuild, path: Path, tiles: TileSettings) -> int:
    """Write GeoJSONSeq for tippecanoe (one feature per line, layer and zooms per feature).

    Layers: il, ilce, birim (neighbourhoods/villages, incl. approximate ones), ozel_bolge
    (special zones mapped as land use) and etiket (label points). Returns the feature count.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    layer_zoom, label_zoom = tiles.layer_min_zoom, tiles.label_min_zoom
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for frame, layer, props in (
            (build.provinces, "il", lambda r: {"id": r.id, "name": r.name, "code": r.code}),
            (
                build.districts.dropna(subset=["province_id"]),
                "ilce",
                lambda r: {"id": r.id, "name": r.name, "il": r.province_id},
            ),
            (
                build.units,
                "birim",
                lambda r: {
                    "id": r.id,
                    "name": r.name,
                    "type": r.type,
                    "approx": bool(r.approx),
                    "il": r.province_id,
                    "ilce": r.district_id,
                },
            ),
            (
                build.special_zones,
                "ozel_bolge",
                lambda r: {"id": r.id, "name": r.name, "il": r.province_id, "ilce": r.district_id},
            ),
        ):
            count += _write_features(
                handle, frame.itertuples(), frame.geometry.values, layer, layer_zoom[layer], props
            )

        for frame, level in (
            (build.provinces, "il"),
            (build.districts.dropna(subset=["province_id"]), "ilce"),
            (build.units, "birim"),
        ):
            points = _label_points(frame.geometry.values, precise=level != "birim")
            count += _write_features(
                handle,
                frame.itertuples(),
                points,
                "etiket",
                label_zoom[level],
                lambda r, level=level: {
                    "id": r.id,
                    "name": r.name,
                    "level": level,
                    "approx": bool(getattr(r, "approx", False)),
                },
            )
    return count


def _label_points(geoms: Iterable[Any], precise: bool) -> list[Any]:
    """Label position inside each polygon: pole of inaccessibility of the largest part for
    provinces/districts (nicer placement), a cheap interior point for small units."""
    points = []
    for geom in geoms:
        if precise:
            largest = max(shapely.get_parts(geom), key=lambda part: part.area)
            points.append(polylabel(largest, tolerance=0.001))
        else:
            points.append(shapely.point_on_surface(geom))
    return points


def _write_features(handle, rows, geoms, layer, min_zoom, props) -> int:
    count = 0
    rounded = shapely.set_precision(list(geoms), COORD_PRECISION)
    for row, geom in zip(rows, rounded, strict=True):
        if geom is None or geom.is_empty:
            continue
        feature = (
            '{"type":"Feature","geometry":'
            + shapely.to_geojson(geom)
            + ',"properties":'
            + json.dumps(props(row), ensure_ascii=False, separators=(",", ":"))
            + ',"tippecanoe":'
            + json.dumps({"layer": layer, "minzoom": min_zoom})
            + "}\n"
        )
        handle.write(feature)
        count += 1
    return count


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
