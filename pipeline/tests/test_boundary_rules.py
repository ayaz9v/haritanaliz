"""Network-free tests for unit classification, geometry repair, hierarchy and Voronoi."""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pytest
import shapely
from shapely.geometry import MultiPolygon, Point, Polygon, box

from haritanaliz.boundaries.approx import split_gap, voronoi_cells
from haritanaliz.boundaries.classify import (
    Classifier,
    is_container,
    is_sub_settlement,
    is_village_part,
    match_key,
)
from haritanaliz.boundaries.geometry import polygonal_part, remove_slivers, repair
from haritanaliz.boundaries.hierarchy import assign_parents

CLASSIFIER = Classifier.from_settings(
    patterns=[r"organize sanayi", r"\bosb\b", r"\bo s b\b", r"serbest bolge"],
    metropolitan=["TR-34", "TR-35"],
)

# --- classification -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "tags", "expected"),
    [
        ("Alsancak Mahallesi", {}, ("mahalle", "ad")),
        ("Cumhuriyet Mah.", {"place": "village"}, ("mahalle", "ad")),  # name wins over tags
        ("Bağlıca Köyü", {}, ("koy", "ad")),
        ("Söğütlü", {"place": "village"}, ("koy", "etiket")),
        ("Kazancılar", {"place": "neighbourhood"}, ("mahalle", "etiket")),
        ("Hamambaşı", {"turkey_class": "mahalle"}, ("mahalle", "etiket")),
        ("Karabayır", {}, ("belirsiz", "yok")),
        ("Organize Sanayi Bölgesi Mahallesi", {}, ("ozel", "ad")),
        ("Kayseri OSB", {}, ("ozel", "ad")),
        ("Mersin Serbest Bölgesi", {}, ("ozel", "ad")),
    ],
)
def test_unit_type(name: str, tags: dict[str, str], expected: tuple[str, str]) -> None:
    assert CLASSIFIER.unit_type(name, tags) == expected


def test_unit_type_uses_hint_place_last() -> None:
    assert CLASSIFIER.unit_type("Karabayır", {}, hint_place="village") == ("koy", "etiket_noktasi")
    assert CLASSIFIER.unit_type(
        "Karabayır", {}, hint_place="suburb", hint_source="ayni_adli_nokta"
    ) == ("mahalle", "ayni_adli_nokta")
    assert CLASSIFIER.unit_type("Karabayır", {}, hint_place="hamlet") == ("belirsiz", "yok")


def test_metropolitan_provinces_have_no_villages() -> None:
    assert CLASSIFIER.apply_metropolitan("koy", "ad", "TR-35") == ("mahalle", "buyuksehir")
    assert CLASSIFIER.apply_metropolitan("belirsiz", "yok", "TR-34") == ("mahalle", "buyuksehir")
    assert CLASSIFIER.apply_metropolitan("koy", "ad", "TR-14") == ("koy", "ad")
    assert CLASSIFIER.apply_metropolitan("ozel", "ad", "TR-35") == ("ozel", "ad")


@pytest.mark.parametrize(
    ("name", "tags", "expected"),
    [
        ("Horhot Mezrası, Kızılcık", {}, True),
        ("Kanduzla Yaylası", {}, True),
        ("Çınarlı Köyü - Dardanos Mevkii", {}, True),
        ("Yukarı Mahalle", {"turkey_class": "mezra"}, True),
        ("Komşu Mahallesi", {}, False),
        ("Alsancak Mahallesi", {}, False),
    ],
)
def test_sub_settlements(name: str, tags: dict[str, str], expected: bool) -> None:
    assert is_sub_settlement(name, tags) is expected


@pytest.mark.parametrize(
    ("name", "level", "tags", "expected"),
    [
        ("Süksün", "7", {}, True),
        ("Tatların Beldesi", "8", {}, True),
        ("Mucur Belediyesi", None, {}, True),
        ("Ürgüp İlçe Merkezi", "8", {}, True),
        ("Kemerhisar Bucağı", "8", {}, True),
        ("Çevreli", "8", {"turkey_class": "belde"}, True),
        ("Merkez Mahallesi", "8", {}, False),
        ("Bucak Mahallesi", "8", {}, False),
    ],
)
def test_containers(name: str, level: str | None, tags: dict[str, str], expected: bool) -> None:
    assert is_container(name, level, tags) is expected


def test_village_parts_and_match_key() -> None:
    assert is_village_part({"place": "neighbourhood", "is_in:village": "Arıca"})
    assert not is_village_part({"place": "neighbourhood"})
    assert match_key("O.S.B. İŞLETMELERİ") == "o s b isletmeleri"


# --- geometry -----------------------------------------------------------------------------


def test_repair_fixes_self_intersection_and_keeps_polygons() -> None:
    bowtie = Polygon([(0, 0), (2, 2), (2, 0), (0, 2), (0, 0)])
    square = box(0, 0, 1, 1)
    repaired, invalid = repair(np.array([bowtie, square], dtype=object))
    assert invalid.tolist() == [True, False]
    assert repaired[0].is_valid
    assert repaired[0].geom_type == "MultiPolygon"
    assert repaired[0].area == pytest.approx(2.0)
    assert repaired[1] is square


def test_polygonal_part_drops_lines_and_points() -> None:
    collection = shapely.GeometryCollection(
        [box(0, 0, 1, 1), shapely.LineString([(0, 0), (5, 5)]), Point(9, 9)]
    )
    assert polygonal_part(collection).equals(box(0, 0, 1, 1))
    assert polygonal_part(shapely.LineString([(0, 0), (1, 1)])) is None
    assert polygonal_part(None) is None


def test_remove_slivers() -> None:
    gap = shapely.union_all([box(0, 0, 100, 100), box(100, 0, 300, 0.5), box(400, 0, 401, 1)])
    cleaned = remove_slivers(gap, width_m=2, min_area_m2=10)
    assert cleaned.area == pytest.approx(10_000, rel=1e-6)


# --- hierarchy ----------------------------------------------------------------------------


def test_assign_parents_by_largest_overlap() -> None:
    parents = gpd.GeoDataFrame(
        {"name": ["A", "B"]}, geometry=[box(0, 0, 10, 10), box(10, 0, 20, 10)], index=["a", "b"]
    )
    children = gpd.GeoDataFrame(
        geometry=[box(1, 1, 3, 3), box(8, 0, 13, 2), box(50, 50, 51, 51)], index=["x", "y", "z"]
    )
    result = assign_parents(children, parents)
    assert result.loc["x", "parent"] == "a"
    assert result.loc["x", "share"] == pytest.approx(1.0)
    assert result.loc["y", "parent"] == "b"  # 3 of 5 units of width lie in B
    assert result.loc["y", "share"] == pytest.approx(0.6)
    assert result.loc["y", "candidates"] == 2
    assert pd_isna(result.loc["z", "parent"])
    assert result.loc["z", "candidates"] == 0


def pd_isna(value: object) -> bool:
    import pandas as pd

    return bool(pd.isna(value))


# --- approximate (Voronoi) boundaries ------------------------------------------------------


def test_voronoi_cells_split_region_between_points() -> None:
    region = box(0, 0, 10, 4)
    cells = voronoi_cells([Point(2, 2), Point(8, 2)], region)
    assert len(cells) == 2
    assert cells[0].area == pytest.approx(20)
    assert cells[1].area == pytest.approx(20)
    assert cells[0].contains(Point(2, 2))
    assert shapely.union_all(cells).equals(region)


def test_voronoi_single_point_gets_whole_region() -> None:
    region = box(0, 0, 3, 3)
    assert voronoi_cells([Point(1, 1)], region) == [region]


def test_split_gap_uses_only_parts_with_points() -> None:
    gap = MultiPolygon([box(0, 0, 10, 10), box(20, 0, 30, 10)])
    points = [Point(2, 5), Point(8, 5), Point(50, 50), Point(2, 5)]
    result = split_gap(gap, points)
    assert sorted(result) == [0, 1]  # outside point and duplicate coordinates are skipped
    assert sum(cell.area for cell in result.values()) == pytest.approx(100)
    assert all(cell.within(box(0, 0, 10, 10).buffer(1e-9)) for cell in result.values())


def test_split_gap_handles_empty_input() -> None:
    assert split_gap(None, [Point(0, 0)]) == {}
    assert split_gap(box(0, 0, 1, 1), []) == {}
