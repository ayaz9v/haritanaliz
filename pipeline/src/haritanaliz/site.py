"""The local site folder: the same layout as on R2 (``manifest.json`` + ``v/<version>/``).

The web app reads it in development through ``VITE_DATA_BASE_URL=/data-local`` (the Vite dev
server serves ``data/output/site`` with HTTP range support for PMTiles).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from haritanaliz.manifest import Manifest, ManifestSource, ManifestVersion

# Files a version may contain, by manifest key. Listed only if present.
KNOWN_FILES = {
    "config": "config.json",
    "regions": "regions/index.json",
    "region_search": "regions/search.json",
    "boundaries": "boundaries.pmtiles",
}
DATA_LICENSE = "ODbL-1.0"
DATA_ATTRIBUTION = "© OpenStreetMap katkıcıları"


def version_dir(site_dir: Path, version: str) -> Path:
    return site_dir / "v" / version


def write_manifest(
    site_dir: Path,
    version: str,
    sources: list[ManifestSource],
    sample: bool = False,
) -> Path:
    """Write ``manifest.json`` pointing at ``version`` with the files that exist in it."""
    folder = version_dir(site_dir, version)
    files = {key: rel for key, rel in KNOWN_FILES.items() if (folder / rel).is_file()}
    manifest = Manifest(
        schema_version=1,
        sample=sample,
        latest=version,
        versions=[
            ManifestVersion(
                version=version,
                path=f"v/{version}/",
                published_at=datetime.now(UTC).replace(microsecond=0),
                files=files,
                sources=sources,
                license=DATA_LICENSE,
                attribution=DATA_ATTRIBUTION,
            )
        ],
    )
    path = site_dir / "manifest.json"
    site_dir.mkdir(parents=True, exist_ok=True)
    data = manifest.model_dump(mode="json", exclude_none=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return path


def osm_source(timestamp: str) -> ManifestSource:
    return ManifestSource(
        id="osm",
        name="OpenStreetMap (Geofabrik Türkiye)",
        version=timestamp,
        license=DATA_LICENSE,
    )
