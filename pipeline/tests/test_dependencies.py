"""Smoke test: the geo and statistics stack declared in CLAUDE.md installs and imports."""

from __future__ import annotations

import importlib

import pytest


@pytest.mark.parametrize(
    "module",
    ["duckdb", "geopandas", "shapely", "statsmodels.api", "libpysal", "esda", "spreg"],
)
def test_module_imports(module: str) -> None:
    importlib.import_module(module)


def test_duckdb_runs_a_query() -> None:
    import duckdb

    assert duckdb.sql("SELECT 6 * 7").fetchone() == (42,)
