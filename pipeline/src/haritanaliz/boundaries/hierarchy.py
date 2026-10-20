"""Attach units to the parent (district, province) they overlap most."""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely


def assign_parents(children: gpd.GeoDataFrame, parents: gpd.GeoDataFrame) -> pd.DataFrame:
    """For every child, the parent with the largest overlap and the child's area share in it.

    Both frames must use the same projected CRS. Returns a frame indexed like ``children``
    with ``parent`` (the parent's index label, or NA), ``share`` (0 to 1) and ``candidates``
    (number of parents the child overlaps).
    """
    result = pd.DataFrame(
        {
            "parent": pd.Series(pd.NA, index=children.index, dtype="object"),
            "share": 0.0,
            "candidates": 0,
        },
    )
    if children.empty or parents.empty:
        return result

    tree = shapely.STRtree(parents.geometry.values)
    child_pos, parent_pos = tree.query(children.geometry.values, predicate="intersects")
    if len(child_pos) == 0:
        return result

    child_geoms = children.geometry.values[child_pos]
    overlap = shapely.area(shapely.intersection(child_geoms, parents.geometry.values[parent_pos]))
    pairs = pd.DataFrame({"child": child_pos, "parent": parent_pos, "overlap": overlap})
    pairs = pairs[pairs["overlap"] > 0]
    if pairs.empty:
        return result

    counts = pairs.groupby("child").size()
    best = pairs.loc[pairs.groupby("child")["overlap"].idxmax()]
    child_area = shapely.area(children.geometry.values[best["child"].to_numpy()])
    shares = np.divide(
        best["overlap"].to_numpy(), child_area, out=np.zeros(len(best)), where=child_area > 0
    )
    labels = children.index[best["child"].to_numpy()]
    result.loc[labels, "parent"] = parents.index[best["parent"].to_numpy()].to_numpy()
    result.loc[labels, "share"] = np.minimum(shares, 1.0)
    result.loc[children.index[counts.index.to_numpy()], "candidates"] = counts.to_numpy()
    return result
