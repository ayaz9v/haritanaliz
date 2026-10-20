"""Vector tiles (PMTiles) with tippecanoe.

tippecanoe has no Windows build. It runs in GitHub Actions (.github/workflows/boundaries.yml)
or, if installed, under WSL/Linux; see docs/decisions.md.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from haritanaliz.boundaries.web import ATTRIBUTION
from haritanaliz.config import TileSettings


class TippecanoeMissingError(RuntimeError):
    """tippecanoe is not installed (it has no Windows build)."""


def find_tippecanoe() -> str | None:
    return shutil.which("tippecanoe")


def tippecanoe_command(
    executable: str, source: Path, target: Path, tiles: TileSettings, name: str
) -> list[str]:
    return [
        executable,
        "--output",
        str(target),
        "--force",
        "--read-parallel",
        "--minimum-zoom=0",
        f"--maximum-zoom={tiles.max_zoom}",
        # Neighbouring polygons share borders; simplify them identically (no slivers).
        "--detect-shared-borders",
        # Boundaries must never be thinned out: keep every feature in every tile.
        "--no-feature-limit",
        "--no-tile-size-limit",
        f"--name={name}",
        f"--attribution={ATTRIBUTION}",
        "--description=haritanaliz idari sınırlar (ODbL 1.0, OpenStreetMap'ten türetilmiştir)",
        str(source),
    ]


def build_tiles(source: Path, target: Path, tiles: TileSettings, name: str) -> Path:
    executable = find_tippecanoe()
    if executable is None:
        raise TippecanoeMissingError(
            "tippecanoe is not installed. On Windows run the GitHub workflow instead: "
            "gh workflow run boundaries.yml (see README.md)"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(tippecanoe_command(executable, source, target, tiles, name), check=True)
    return target
