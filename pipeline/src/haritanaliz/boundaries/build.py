"""Build the boundary dataset from the OSM extract.

Steps (see docs/decisions.md and docs/reports/sinir_kalitesi.md for the evidence behind them):

1. Repair geometries; keep administrative polygons whose interior point lies in Türkiye.
2. Provinces: admin_level=4 with ISO3166-2 "TR-xx". Their land part (the polygons include
   territorial waters) is the province clipped to the union of its districts.
3. Districts: admin_level=6 relations, except islands tagged with a district level that lie
   inside another district.
4. Unit candidates: admin_level 7 to 10 and polygons with a missing/invalid level but a unit
   name. Sub-settlements (mezra, yayla, mevki) and village parts are dropped; municipal
   containers (belde, district/provincial centre areas) are kept apart.
5. Each unit gets a type (mahalle, koy, ozel, belirsiz) and the district it overlaps most.
6. Per district, uncovered land is split among place points with a Voronoi diagram
   (approximate boundaries, ``approx=True``).
7. Organised industrial zones and free zones mapped as land use are kept as a separate layer.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from haritanaliz.boundaries.approx import split_gap
from haritanaliz.boundaries.classify import (
    PLACE_TO_TYPE,
    Classifier,
    is_container,
    is_sub_settlement,
    is_village_part,
)
from haritanaliz.boundaries.geometry import remove_slivers, repair
from haritanaliz.boundaries.hierarchy import assign_parents
from haritanaliz.config import BoundarySettings
from haritanaliz.osm.extract import OsmBoundaryExtract
from haritanaliz.text import display_name, normalize_name, split_type_suffix

WGS84 = "EPSG:4326"
UNIT_LEVELS = ("7", "8", "9", "10")
KNOWN_LEVELS = frozenset(str(level) for level in range(2, 12))
SLIVER_WIDTH_M = 10.0
PLACE_PRIORITY = {"village": 0, "suburb": 1, "neighbourhood": 2, "quarter": 3}


@dataclass
class BoundaryBuild:
    """Result of :func:`build_boundaries`. Geometries are in EPSG:4326."""

    provinces: gpd.GeoDataFrame
    districts: gpd.GeoDataFrame
    units: gpd.GeoDataFrame
    containers: gpd.GeoDataFrame
    special_zones: gpd.GeoDataFrame
    excluded: pd.DataFrame
    coverage: pd.DataFrame
    issues: pd.DataFrame
    stats: dict[str, Any] = field(default_factory=dict)


def osm_ref(osm_type: str, osm_id: int) -> str:
    """Persistent id from the OSM object: r123 (relation), w123 (way), n123 (node)."""
    return f"{osm_type[0]}{osm_id}"


def build_boundaries(
    extract: OsmBoundaryExtract,
    settings: BoundarySettings,
    log: Any = None,
) -> BoundaryBuild:
    say = log or (lambda message: None)
    crs = settings.area_crs
    classifier = Classifier.from_settings(
        settings.special_zone_patterns, settings.metropolitan_provinces
    )
    stats: dict[str, Any] = {}
    issues: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    # 1. Geometry repair and projection ---------------------------------------------------
    areas = extract.areas.copy()
    areas["tags_d"] = areas["tags"].map(json.loads)
    repaired, invalid = repair(areas.geometry.values)
    stats["invalid_geometries"] = int(invalid.sum())
    for row in areas[invalid].itertuples():
        issues.append(_issue("geometri_onarildi", osm_ref(row.osm_type, row.osm_id), row.name))
    areas = areas.set_geometry(gpd.GeoSeries(repaired, index=areas.index, crs=WGS84))
    areas = areas[areas.geometry.notna()].to_crs(crs)
    areas["id"] = [osm_ref(t, i) for t, i in zip(areas["osm_type"], areas["osm_id"], strict=True)]

    nodes = extract.place_nodes.copy()
    nodes["tags_d"] = nodes["tags"].map(json.loads)
    nodes = nodes.to_crs(crs)

    is_admin = areas["boundary"] == "administrative"
    country = _country(areas[is_admin], settings.country_iso)
    interior = areas.geometry.representative_point()
    in_country = pd.Series(shapely.contains(country, interior.values), index=areas.index)
    admin = areas[is_admin & in_country].copy()
    nodes = nodes[shapely.contains(country, nodes.geometry.values)].copy()
    stats["admin_polygons_in_country"] = len(admin)
    stats["admin_levels"] = {
        str(level): int(count)
        for level, count in admin["admin_level"].fillna("yok").value_counts().items()
    }
    stats["place_points"] = {
        str(place): int(count) for place, count in nodes["place"].value_counts().items()
    }
    say(f"{len(admin):,} administrative polygons and {len(nodes):,} place points in Türkiye")

    # 2. Provinces -------------------------------------------------------------------------
    iso = admin["tags_d"].map(lambda t: t.get("ISO3166-2", ""))
    provinces = admin[(admin["admin_level"] == "4") & iso.str.startswith("TR-")].copy()
    provinces["iso"] = iso[provinces.index]
    provinces["code"] = provinces["iso"].str.removeprefix("TR-")
    provinces = provinces.set_index("id", drop=False).sort_values("code")
    provinces["area_total_km2"] = provinces.area / 1e6
    stats["provinces"] = len(provinces)

    # 3. Districts -------------------------------------------------------------------------
    level6 = admin[admin["admin_level"] == "6"]
    relations6 = level6[level6["osm_type"] == "relation"]
    island = relations6["place"].isin(["island", "islet"])
    inside_other = _inside_other(relations6[island], relations6[~island])
    for row in relations6[island][inside_other].itertuples():
        excluded.append(_excluded(row, "ada_ilce_degil", "ada; başka bir ilçenin içinde"))
    districts = relations6[~(island & island.index.isin(inside_other[inside_other].index))].copy()
    districts = districts.set_index("id", drop=False)

    district_parent = assign_parents(districts, provinces)
    districts["province_id"] = district_parent["parent"]
    districts["parent_share"] = district_parent["share"]
    for row in districts[districts["parent_share"] < 0.99].itertuples():
        issues.append(
            _issue(
                "ilce_il_tasmasi", row.id, row.name, f"ilin içinde kalan pay {row.parent_share:.3f}"
            )
        )
    stats["districts"] = int(districts["province_id"].notna().sum())

    # Province land = province ∩ union(districts): drops territorial waters.
    land = {}
    for province_id, group in districts.groupby("province_id"):
        land[province_id] = shapely.intersection(
            provinces.at[province_id, "geometry"], shapely.union_all(group.geometry.values)
        )
    provinces["geometry"] = [land.get(pid, geom) for pid, geom in provinces.geometry.items()]
    provinces = provinces.set_geometry("geometry", crs=crs)
    provinces["area_km2"] = provinces.area / 1e6
    districts["area_km2"] = districts.area / 1e6

    # 4. Unit candidates -------------------------------------------------------------------
    ways6 = level6[level6["osm_type"] == "way"]
    way_units = ways6["name"].fillna("").map(lambda n: split_type_suffix(n)[1] is not None)
    for row in ways6[~way_units].itertuples():
        excluded.append(_excluded(row, "ilce_seviyesinde_way", "ilçe seviyesinde kapalı way"))
    odd_level = ~admin["admin_level"].isin(KNOWN_LEVELS)
    named_like_unit = (
        admin["name"]
        .fillna("")
        .map(lambda n: split_type_suffix(n)[1] is not None or is_container(n, None, {}))
    )
    candidates = pd.concat(
        [
            admin[admin["admin_level"].isin(UNIT_LEVELS)],
            admin[odd_level & named_like_unit],
            ways6[way_units],
        ]
    )
    candidates = candidates[~candidates.index.duplicated()].copy()
    for row in candidates[odd_level.reindex(candidates.index, fill_value=False)].itertuples():
        issues.append(
            _issue(
                "admin_level_eksik_hatali",
                row.id,
                row.name,
                f"admin_level={row.admin_level if isinstance(row.admin_level, str) else 'yok'}",
            )
        )
    for row in admin[odd_level & ~named_like_unit].itertuples():
        excluded.append(
            _excluded(row, "seviyesiz_birim_disi", "admin_level eksik/hatalı, adı birim değil")
        )

    unnamed = candidates["name"].isna()
    for row in candidates[unnamed].itertuples():
        excluded.append(_excluded(row, "adsiz", "adı yok"))
    candidates = candidates[~unnamed]

    sub = [
        is_sub_settlement(n, t)
        for n, t in zip(candidates["name"], candidates["tags_d"], strict=True)
    ]
    sub = pd.Series(sub, index=candidates.index)
    for row in candidates[sub].itertuples():
        excluded.append(_excluded(row, "alt_yerlesim", "mezra/yayla/mevki"))
    candidates = candidates[~sub]

    container_mask = pd.Series(
        [
            is_container(n, lvl, t)
            for n, lvl, t in zip(
                candidates["name"], candidates["admin_level"], candidates["tags_d"], strict=True
            )
        ],
        index=candidates.index,
    )
    containers = candidates[container_mask].copy()
    units = candidates[~container_mask].copy()

    # Units mapped one level below another unit (village quarters etc.) are parts, not units.
    nested = _nested_deeper(units)
    for row in units[nested].itertuples():
        excluded.append(
            _excluded(
                row, "birim_ici_alt_birim", "başka bir köy/mahallenin içinde, daha derin seviye"
            )
        )
    units = units[~nested].set_index("id", drop=False)

    # The same unit mapped twice (e.g. as a way and as a relation): keep one.
    duplicate = _duplicates(units, settings.duplicate_iou)
    for row in units[duplicate].itertuples():
        excluded.append(_excluded(row, "yinelenen_birim", "aynı birim ikinci kez çizilmiş"))
    units = units[~duplicate]

    # Old village/municipality outlines kept around the mahalle drawn inside them, at the
    # same admin level: they are containers, not units.
    enclosing = _enclosing(units, settings.container_share)
    stats["containers_by_name_or_level"] = len(containers)
    stats["containers_by_nesting"] = int(enclosing.sum())
    containers = pd.concat([containers, units[enclosing]]).set_index("id", drop=False)
    containers = containers[~containers.index.duplicated()]
    units = units[~enclosing]
    stats["candidate_units"] = len(units)

    # 5. Hierarchy and types ---------------------------------------------------------------
    unit_parent = assign_parents(units, districts)
    units["district_id"] = unit_parent["parent"]
    units["parent_share"] = unit_parent["share"]
    outside = units["district_id"].isna()
    for row in units[outside].itertuples():
        excluded.append(_excluded(row, "ilce_disinda", "hiçbir ilçeyle kesişmiyor"))
    units = units[~outside].copy()
    for row in units[units["parent_share"] < settings.min_parent_share].itertuples():
        issues.append(
            _issue(
                "birden_fazla_ilceye_tasma",
                row.id,
                row.name,
                f"en büyük ilçe payı {row.parent_share:.2f}",
            )
        )
    units["province_id"] = districts.loc[units["district_id"], "province_id"].to_numpy()

    container_parent = assign_parents(containers, districts)
    containers["district_id"] = container_parent["parent"]
    containers = containers[containers["district_id"].notna()].copy()
    containers["province_id"] = districts.loc[containers["district_id"], "province_id"].to_numpy()

    province_iso = provinces["iso"]
    units["name_key"] = units["name"].map(normalize_name)
    label_place = _label_places(extract.admin_relations, nodes)
    same_name_place = _same_name_places(units, nodes)
    types, sources = [], []
    for row in units.itertuples():
        hint = label_place.get(row.osm_id) if row.osm_type == "relation" else None
        hint_source = "etiket_noktasi"
        if hint is None:
            hint, hint_source = same_name_place.get(row.id), "ayni_adli_nokta"
        unit_type, source = classifier.unit_type(row.name, row.tags_d, hint, hint_source)
        unit_type, source = classifier.apply_metropolitan(
            unit_type, source, province_iso.get(row.province_id)
        )
        types.append(unit_type)
        sources.append(source)
    units["type"] = types
    units["type_source"] = sources
    units["approx"] = False

    # 6. Coverage and approximate boundaries ------------------------------------------------
    candidates_points = _approx_candidates(nodes, areas, settings)
    urban = _near_urban(candidates_points, nodes, containers, settings)
    quarter_like = candidates_points["place"].isin(["neighbourhood", "suburb", "quarter"])
    village_quarters = quarter_like & ~urban
    stats["approx_dropped_village_quarters"] = int(village_quarters.sum())
    candidates_points = candidates_points[~village_quarters]
    approx_rows, coverage_rows = [], []
    min_gap_m2 = settings.min_gap_km2 * 1e6
    units_by_district = dict(tuple(units.groupby("district_id")))
    points_by_district = _points_by_district(candidates_points, districts)

    for district_id, district in districts.iterrows():
        if pd.isna(district["province_id"]):
            continue
        dgeom = district.geometry
        dunits = units_by_district.get(district_id)
        clipped = shapely.intersection(dunits.geometry.values, dgeom) if dunits is not None else []
        covered = shapely.union_all(clipped) if len(clipped) else shapely.Polygon()
        overlap = (
            max(0.0, float(np.sum(shapely.area(clipped)) - covered.area)) if len(clipped) else 0.0
        )
        gap = remove_slivers(shapely.difference(dgeom, covered), SLIVER_WIDTH_M, min_gap_m2)

        new_units = []
        points = points_by_district.get(district_id)
        if gap is not None and points is not None and len(points):
            existing = set(dunits["name_key"]) if dunits is not None else set()
            points = points[~points["name_norm"].isin(existing)]
            cells = split_gap(gap, list(points.geometry.values))
            for position, cell in cells.items():
                point = points.iloc[position]
                new_units.append((point, cell))
        approx_covered = (
            shapely.union_all([cell for _, cell in new_units]) if new_units else shapely.Polygon()
        )
        remaining = (
            remove_slivers(shapely.difference(gap, approx_covered), SLIVER_WIDTH_M, min_gap_m2)
            if gap is not None
            else None
        )
        for point, cell in new_units:
            approx_rows.append(
                {
                    "id": point["id"],
                    "osm_type": point["osm_type"],
                    "osm_id": point["osm_id"],
                    "name": point["name"],
                    "admin_level": None,
                    "tags_d": point["tags_d"],
                    "district_id": district_id,
                    "province_id": district["province_id"],
                    "parent_share": 1.0,
                    "place": point["place"],
                    "geometry": cell,
                }
            )
        area = dgeom.area
        coverage_rows.append(
            {
                "district_id": district_id,
                "province_id": district["province_id"],
                "units": 0 if dunits is None else len(dunits),
                "approx_units": len(new_units),
                "area_km2": area / 1e6,
                "covered_km2": covered.area / 1e6,
                "approx_km2": approx_covered.area / 1e6,
                "overlap_km2": overlap / 1e6,
                "gap_km2": 0.0 if remaining is None else remaining.area / 1e6,
                "gap_before_km2": 0.0 if gap is None else gap.area / 1e6,
                "points_in_gap": 0 if points is None else len(points),
            }
        )

    approx = gpd.GeoDataFrame(approx_rows, geometry="geometry", crs=crs)
    if not approx.empty:
        approx = approx.set_index("id", drop=False)
        types, sources = [], []
        for row in approx.itertuples():
            unit_type, source = classifier.unit_type(row.name, row.tags_d, row.place, "etiket")
            unit_type, source = classifier.apply_metropolitan(
                unit_type, source, province_iso.get(row.province_id)
            )
            types.append(unit_type)
            sources.append(source)
        approx["type"] = types
        approx["type_source"] = sources
        approx["approx"] = True
    stats["approx_units"] = len(approx)
    say(f"{len(units):,} units with OSM boundaries, {len(approx):,} approximate units")

    columns = [
        "id",
        "osm_type",
        "osm_id",
        "name",
        "admin_level",
        "type",
        "type_source",
        "approx",
        "district_id",
        "province_id",
        "parent_share",
        "geometry",
    ]
    all_units = pd.concat([units[columns], approx[columns] if not approx.empty else None])
    all_units = gpd.GeoDataFrame(all_units, geometry="geometry", crs=crs)
    duplicated = all_units.index.duplicated()
    for unit_id in all_units.index[duplicated]:
        issues.append(_issue("yinelenen_kimlik", unit_id, None, "aynı OSM nesnesi iki kez"))
    all_units = all_units[~duplicated]
    all_units["area_km2"] = all_units.area / 1e6

    # 7. Special zones mapped as land use -------------------------------------------------
    special_zones = _special_zones(areas[in_country], classifier, districts)

    coverage = pd.DataFrame(coverage_rows).set_index("district_id")
    stats["type_counts"] = dict(Counter(all_units["type"]))
    stats["type_counts_real"] = dict(Counter(all_units.loc[~all_units["approx"], "type"]))
    stats["type_source_counts"] = dict(Counter(all_units["type_source"]))
    stats["containers"] = len(containers)
    stats["special_zones"] = len(special_zones)

    # Names, then back to WGS84 ----------------------------------------------------------
    provinces = _with_names(provinces, display=False)
    districts = _with_names(districts, display=False)
    all_units = _with_names(all_units, display=True)
    containers = _with_names(containers, display=True)

    issues.extend(_failed_relations(extract.admin_relations))
    return BoundaryBuild(
        provinces=provinces[
            [
                "id",
                "osm_type",
                "osm_id",
                "name",
                "name_full",
                "name_norm",
                "iso",
                "code",
                "area_km2",
                "area_total_km2",
                "geometry",
            ]
        ].to_crs(WGS84),
        districts=districts[
            [
                "id",
                "osm_type",
                "osm_id",
                "name",
                "name_full",
                "name_norm",
                "province_id",
                "parent_share",
                "area_km2",
                "geometry",
            ]
        ].to_crs(WGS84),
        units=all_units.to_crs(WGS84),
        containers=containers[
            [
                "id",
                "osm_type",
                "osm_id",
                "name",
                "name_full",
                "admin_level",
                "district_id",
                "province_id",
                "geometry",
            ]
        ].to_crs(WGS84),
        special_zones=special_zones.to_crs(WGS84),
        excluded=pd.DataFrame(excluded, columns=["id", "name", "admin_level", "reason", "detail"]),
        coverage=coverage,
        issues=pd.DataFrame(issues, columns=["kind", "id", "name", "detail"]),
        stats=stats,
    )


# ------------------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------------------


def _country(admin: gpd.GeoDataFrame, country_iso: str) -> Any:
    level2 = admin[admin["admin_level"] == "2"]
    codes = level2["tags_d"].map(lambda t: t.get("ISO3166-1") or t.get("ISO3166-1:alpha2"))
    match = level2[codes == country_iso]
    if match.empty:
        raise ValueError(f"no admin_level=2 polygon with ISO3166-1={country_iso} in the extract")
    return match.geometry.iloc[0]


def _inside_other(
    inner: gpd.GeoDataFrame, outer: gpd.GeoDataFrame, share: float = 0.9
) -> pd.Series:
    """True for polygons of ``inner`` that lie (mostly) inside a polygon of ``outer``."""
    result = assign_parents(inner, outer)
    return result["share"] >= share


def _nested_deeper(units: gpd.GeoDataFrame) -> pd.Series:
    """Units whose interior point lies in another unit with a smaller (shallower) admin level."""
    level = pd.to_numeric(units["admin_level"], errors="coerce")
    nested = pd.Series(False, index=units.index)
    deep = units[level.notna() & (level > 8)]
    if deep.empty:
        return nested
    shallow = units[level.notna() & (level <= 8)]
    tree = shapely.STRtree(shallow.geometry.values)
    deep_pos, shallow_pos = tree.query(
        deep.geometry.representative_point().values, predicate="within"
    )
    deep_levels = level[deep.index].to_numpy()[deep_pos]
    shallow_levels = level[shallow.index].to_numpy()[shallow_pos]
    hits = deep.index[deep_pos[deep_levels > shallow_levels]]
    nested[hits] = True
    return nested


def _duplicates(units: gpd.GeoDataFrame, iou_threshold: float) -> pd.Series:
    """Units repeating another unit's geometry (intersection over union at or above the
    threshold). The relation, or else the lower OSM id, is kept."""
    mask = np.zeros(len(units), dtype=bool)
    geoms = units.geometry.values
    tree = shapely.STRtree(geoms)
    first, second = tree.query(geoms, predicate="intersects")
    pair = first < second
    first, second = first[pair], second[pair]
    inter = shapely.area(shapely.intersection(geoms[first], geoms[second]))
    union = shapely.area(geoms[first]) + shapely.area(geoms[second]) - inter
    same = inter >= iou_threshold * union
    rank = np.where(units["osm_type"].to_numpy() == "relation", 0, 1) * 10**13 + units[
        "osm_id"
    ].to_numpy().astype(np.int64)
    for a, b in zip(first[same], second[same], strict=True):
        mask[a if rank[a] > rank[b] else b] = True
    return pd.Series(mask, index=units.index)


def _enclosing(units: gpd.GeoDataFrame, share: float) -> pd.Series:
    """Units whose area is covered at least ``share`` by smaller units lying inside them."""
    mask = np.zeros(len(units), dtype=bool)
    geoms = units.geometry.values
    areas = shapely.area(geoms)
    tree = shapely.STRtree(geoms)
    inner, outer = tree.query(shapely.point_on_surface(geoms), predicate="within")
    keep = (inner != outer) & (areas[inner] < areas[outer])
    inner, outer = inner[keep], outer[keep]
    inside = shapely.area(shapely.intersection(geoms[inner], geoms[outer])) >= 0.95 * areas[inner]
    pairs = pd.DataFrame({"outer": outer[inside], "inner": inner[inside]})
    for position, group in pairs.groupby("outer"):
        covered = shapely.union_all(geoms[group["inner"].to_numpy()]).area
        if covered >= share * areas[position]:
            mask[position] = True
    return pd.Series(mask, index=units.index)


def _near_urban(
    points: gpd.GeoDataFrame,
    nodes: gpd.GeoDataFrame,
    containers: gpd.GeoDataFrame,
    settings: BoundarySettings,
) -> pd.Series:
    """Points near a town/city point or inside a municipal area (container polygon)."""
    near = np.zeros(len(points), dtype=bool)
    geoms = points.geometry.values
    radius = settings.urban_radius_km
    for place, radius_km in (("town", radius.town), ("city", radius.city)):
        anchors = nodes.loc[nodes["place"] == place].geometry.values
        if len(anchors):
            hits, _ = shapely.STRtree(anchors).query(
                geoms, predicate="dwithin", distance=radius_km * 1000
            )
            near[np.unique(hits)] = True
    if len(containers):
        hits, _ = shapely.STRtree(containers.geometry.values).query(geoms, predicate="within")
        near[np.unique(hits)] = True
    return pd.Series(near, index=points.index)


def _label_places(relations: pd.DataFrame, nodes: gpd.GeoDataFrame) -> dict[int, str]:
    """relation id -> place tag of its label member node (if that node is a place point)."""
    place_by_node = dict(zip(nodes["osm_id"], nodes["place"], strict=True))
    result = {}
    for rel_id, node_id in zip(relations["osm_id"], relations["label_node"], strict=True):
        if pd.notna(node_id) and int(node_id) in place_by_node:
            result[int(rel_id)] = place_by_node[int(node_id)]
    return result


def _same_name_places(units: gpd.GeoDataFrame, nodes: gpd.GeoDataFrame) -> dict[str, str]:
    """unit id -> place tag of a place point with the same normalized name inside the unit.

    ``units`` needs a ``name_key`` column (normalized name)."""
    relevant = nodes[nodes["place"].isin(list(PLACE_TO_TYPE))].copy()
    relevant["name_norm"] = relevant["name"].fillna("").map(normalize_name)
    joined = gpd.sjoin(
        relevant[["name_norm", "place", "geometry"]],
        units[["name_key", "geometry"]].rename_axis(None),
        predicate="within",
    )
    joined = joined[joined["name_norm"] == joined["name_key"]]
    joined = joined.assign(priority=joined["place"].map(PLACE_PRIORITY)).sort_values("priority")
    return joined.groupby("index_right")["place"].first().to_dict()


def _approx_candidates(
    nodes: gpd.GeoDataFrame, areas: gpd.GeoDataFrame, settings: BoundarySettings
) -> gpd.GeoDataFrame:
    """Named place points that can represent a neighbourhood/village without a polygon."""
    allowed = set(settings.approx_place_values)

    def usable(name: Any, tags: dict[str, str]) -> bool:
        return (
            isinstance(name, str)
            and bool(name.strip())
            and not is_sub_settlement(name, tags)
            and not is_village_part(tags)
            and tags.get("turkey_class") != "belde"
        )

    point_rows = nodes[nodes["place"].isin(allowed)].copy()
    point_rows = point_rows[
        [usable(n, t) for n, t in zip(point_rows["name"], point_rows["tags_d"], strict=True)]
    ]
    point_rows["osm_type"] = "node"
    point_rows["id"] = [f"n{i}" for i in point_rows["osm_id"]]

    # Places mapped as polygons without an administrative boundary: use an interior point.
    place_areas = areas[
        areas["place"].isin(allowed) & (areas["boundary"] != "administrative")
    ].copy()
    place_areas = place_areas[
        [usable(n, t) for n, t in zip(place_areas["name"], place_areas["tags_d"], strict=True)]
    ]
    place_areas["geometry"] = place_areas.geometry.representative_point()

    columns = ["id", "osm_type", "osm_id", "name", "place", "tags_d", "geometry"]
    combined = pd.concat([point_rows[columns], place_areas[columns]], ignore_index=True)
    combined = gpd.GeoDataFrame(combined, geometry="geometry", crs=nodes.crs)
    combined["name_norm"] = combined["name"].map(normalize_name)
    combined["priority"] = combined["place"].map(PLACE_PRIORITY).fillna(9)
    return combined


def _points_by_district(
    points: gpd.GeoDataFrame, districts: gpd.GeoDataFrame
) -> dict[str, gpd.GeoDataFrame]:
    """Candidate points per district, one per normalized name (village beats suburb etc.)."""
    joined = gpd.sjoin(points, districts[["geometry"]].rename_axis(None), predicate="within")
    joined = joined.sort_values(["index_right", "priority", "osm_id"])
    joined = joined.drop_duplicates(subset=["index_right", "name_norm"])
    return {
        key: group.drop(columns=["index_right"]) for key, group in joined.groupby("index_right")
    }


def _special_zones(
    areas: gpd.GeoDataFrame, classifier: Classifier, districts: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    candidates = areas[
        ((areas["landuse"] == "industrial") | (areas["boundary"] == "special_economic_zone"))
        & (areas["boundary"] != "administrative")
    ]
    zones = candidates[
        candidates["name"].map(lambda n: classifier.is_special_zone(n))
        | (candidates["boundary"] == "special_economic_zone")
    ].copy()
    zones = zones.set_index("id", drop=False)
    parent = assign_parents(zones, districts)
    zones["district_id"] = parent["parent"]
    zones = zones[zones["district_id"].notna()].copy()
    zones["province_id"] = districts.loc[zones["district_id"], "province_id"].to_numpy()
    zones["area_km2"] = zones.area / 1e6
    zones["name_full"] = zones["name"]
    return zones[
        [
            "id",
            "osm_type",
            "osm_id",
            "name",
            "name_full",
            "district_id",
            "province_id",
            "area_km2",
            "geometry",
        ]
    ]


def _with_names(frame: gpd.GeoDataFrame, display: bool) -> gpd.GeoDataFrame:
    frame = frame.copy()
    frame["name_full"] = frame["name"]
    if display:
        frame["name"] = frame["name_full"].map(display_name)
    frame["name_norm"] = frame["name_full"].map(normalize_name)
    return frame


def _failed_relations(relations: pd.DataFrame) -> list[dict[str, Any]]:
    """Turkish administrative relations libosmium could not assemble (broken rings)."""
    failed = relations[
        ~relations["assembled"] & relations["admin_level"].isin(["4", "6", "7", "8"])
    ]
    turkish = failed["name"].fillna("").map(lambda n: split_type_suffix(n)[1] is not None)
    return [
        _issue("birlesmeyen_iliski", f"r{row.osm_id}", row.name, "halkalar kapanmıyor")
        for row in failed[turkish].itertuples()
    ]


def _issue(kind: str, ident: str, name: Any, detail: str = "") -> dict[str, Any]:
    return {"kind": kind, "id": ident, "name": name, "detail": detail}


def _excluded(row: Any, reason: str, detail: str) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "admin_level": row.admin_level,
        "reason": reason,
        "detail": detail,
    }
