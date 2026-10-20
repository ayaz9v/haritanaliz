"""Save and load a boundary build (GeoParquet + JSON stats) between pipeline commands."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import geopandas as gpd
import pandas as pd

from haritanaliz.boundaries.build import BoundaryBuild

GEO_TABLES = ("provinces", "districts", "units", "containers", "special_zones")
TABLES = ("excluded", "issues")


def save_build(build: BoundaryBuild, folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for name in GEO_TABLES:
        getattr(build, name).to_parquet(folder / f"{name}.parquet")
    for name in TABLES:
        getattr(build, name).to_parquet(folder / f"{name}.parquet")
    build.coverage.to_parquet(folder / "coverage.parquet")
    (folder / "stats.json").write_text(
        json.dumps(build.stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def load_build(folder: Path) -> BoundaryBuild:
    if not (folder / "stats.json").is_file():
        raise FileNotFoundError(
            f"no boundary build in {folder}; run `haritanaliz boundaries` first"
        )
    geo = {name: gpd.read_parquet(folder / f"{name}.parquet") for name in GEO_TABLES}
    plain = {name: pd.read_parquet(folder / f"{name}.parquet") for name in TABLES}
    return BoundaryBuild(
        **geo,
        **plain,
        coverage=pd.read_parquet(folder / "coverage.parquet"),
        stats=json.loads((folder / "stats.json").read_text(encoding="utf-8")),
    )


def only_province(build: BoundaryBuild, province_code: str) -> BoundaryBuild:
    """Everything of one province only (its outline and districts too), e.g. for sample tiles."""
    subset = subset_province(build, province_code)
    province = build.provinces[build.provinces["code"] == province_code]
    return replace(
        subset,
        provinces=province,
        districts=build.districts[build.districts["province_id"].isin(province["id"])],
    )


def subset_province(build: BoundaryBuild, province_code: str) -> BoundaryBuild:
    """Keep all provinces and districts, but units and special zones of one province only."""
    match = build.provinces[build.provinces["code"] == province_code]
    if match.empty:
        raise ValueError(f"unknown province code {province_code}")
    province_id = match["id"].iloc[0]
    return BoundaryBuild(
        provinces=build.provinces,
        districts=build.districts,
        units=build.units[build.units["province_id"] == province_id],
        containers=build.containers[build.containers["province_id"] == province_id],
        special_zones=build.special_zones[build.special_zones["province_id"] == province_id],
        excluded=build.excluded.iloc[0:0],
        coverage=build.coverage[build.coverage["province_id"] == province_id],
        issues=build.issues.iloc[0:0],
        stats={"sample_province": province_code},
    )
