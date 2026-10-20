"""Download the Geofabrik Türkiye extract, verify its MD5 checksum and store it by data date.

The file is saved as ``turkey-YYYY-MM-DD.osm.pbf`` where the date is the OSM data timestamp
from the PBF header (``osmosis_replication_timestamp``), not the download date. A JSON sidecar
next to it records the URL, checksum, size and timestamp; that timestamp becomes the OSM
source version in manifest.json.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import osmium

USER_AGENT = "haritanaliz/0.1 (+https://github.com/ayaz9v/haritanaliz)"
CHUNK_SIZE = 1024 * 1024
PROGRESS_STEP = 50 * 1024 * 1024
# Not matched by the "turkey-*.osm.pbf" pattern, so an unfinished download is never used.
PARTIAL_NAME = "download.partial.osm.pbf"


class DownloadError(RuntimeError):
    """The download failed or the checksum did not match."""


@dataclass(frozen=True)
class OsmExtract:
    path: Path
    url: str
    md5: str
    size: int
    timestamp: datetime

    @property
    def date(self) -> str:
        """Data date (UTC) of the extract, YYYY-MM-DD."""
        return self.timestamp.strftime("%Y-%m-%d")

    @property
    def sidecar(self) -> Path:
        return sidecar_path(self.path)

    def to_json(self) -> dict[str, object]:
        return {
            "file": self.path.name,
            "url": self.url,
            "md5": self.md5,
            "size": self.size,
            "timestamp": self.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }


def dated_url(latest_url: str, day: date) -> str:
    """Geofabrik keeps dated copies: turkey-latest.osm.pbf -> turkey-YYMMDD.osm.pbf."""
    if "-latest.osm.pbf" not in latest_url:
        raise DownloadError(f"cannot derive a dated URL from {latest_url}")
    return latest_url.replace("-latest.osm.pbf", f"-{day:%y%m%d}.osm.pbf")


def find_extract(osm_dir: Path, day: str | None) -> OsmExtract | None:
    """The extract with data date ``day`` (YYYY-MM-DD), or the latest one."""
    if day is None:
        return latest_extract(osm_dir)
    path = osm_dir / f"turkey-{day}.osm.pbf"
    return read_extract(path) if path.is_file() and sidecar_path(path).is_file() else None


def sidecar_path(pbf_path: Path) -> Path:
    return pbf_path.with_name(pbf_path.name.removesuffix(".osm.pbf") + ".json")


def read_extract(pbf_path: Path) -> OsmExtract:
    """Load an extract's metadata from its JSON sidecar."""
    data = json.loads(sidecar_path(pbf_path).read_text(encoding="utf-8"))
    return OsmExtract(
        path=pbf_path,
        url=data["url"],
        md5=data["md5"],
        size=int(data["size"]),
        timestamp=parse_timestamp(data["timestamp"]),
    )


def latest_extract(osm_dir: Path) -> OsmExtract | None:
    """The most recent downloaded extract in ``osm_dir`` (by data date), if any."""
    candidates = sorted(p for p in osm_dir.glob("turkey-*.osm.pbf") if sidecar_path(p).is_file())
    return read_extract(candidates[-1]) if candidates else None


def parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def pbf_timestamp(pbf_path: Path) -> datetime:
    """The OSM data timestamp stored in the PBF header by Geofabrik."""
    # Pass the format explicitly: libosmium otherwise guesses it from the file name.
    header = osmium.io.Reader(osmium.io.File(str(pbf_path), "pbf"), osmium.osm.NOTHING).header()
    value = header.get("osmosis_replication_timestamp", "")
    if not value:
        raise DownloadError(f"{pbf_path.name}: no osmosis_replication_timestamp in the header")
    return parse_timestamp(value)


def fetch_expected_md5(url: str) -> str:
    """Read Geofabrik's ``<file>.md5`` ("<hash>  <name>") for ``url``."""
    with _open(url + ".md5") as response:
        text = response.read().decode("ascii").strip()
    checksum = text.split()[0].lower() if text else ""
    if len(checksum) != 32:
        raise DownloadError(f"unexpected checksum file content: {text!r}")
    return checksum


def download_extract(
    url: str,
    osm_dir: Path,
    progress: Callable[[int, int | None], None] | None = None,
) -> tuple[OsmExtract, bool]:
    """Download ``url`` into ``osm_dir`` unless the same file (by checksum) is already there.

    Returns the extract and whether a new file was downloaded.
    """
    osm_dir.mkdir(parents=True, exist_ok=True)
    expected = fetch_expected_md5(url)

    for existing in sorted(osm_dir.glob("turkey-*.osm.pbf")):
        if sidecar_path(existing).is_file():
            extract = read_extract(existing)
            if extract.md5 == expected and existing.stat().st_size == extract.size:
                return extract, False

    partial = osm_dir / PARTIAL_NAME
    if partial.is_file() and file_md5(partial) == expected:
        # A previous run downloaded the file but stopped before renaming it.
        digest, size = expected, partial.stat().st_size
    else:
        digest, size = _stream_to_file(url, partial, progress)
    if digest != expected:
        # Geofabrik may have published a new file while we were downloading.
        latest = fetch_expected_md5(url)
        partial.unlink(missing_ok=True)
        raise DownloadError(
            f"checksum mismatch: got {digest}, expected {expected}"
            + (
                " (the extract was updated during the download; try again)"
                if latest != expected
                else ""
            )
        )

    timestamp = pbf_timestamp(partial)
    target = osm_dir / f"turkey-{timestamp:%Y-%m-%d}.osm.pbf"
    partial.replace(target)
    extract = OsmExtract(path=target, url=url, md5=digest, size=size, timestamp=timestamp)
    extract.sidecar.write_text(
        json.dumps(extract.to_json(), indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return extract, True


def file_md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def _stream_to_file(
    url: str, target: Path, progress: Callable[[int, int | None], None] | None
) -> tuple[str, int]:
    digest = hashlib.md5(usedforsecurity=False)
    size = 0
    next_report = PROGRESS_STEP
    with _open(url) as response, target.open("wb") as handle:
        total = int(response.headers.get("Content-Length", 0)) or None
        while chunk := response.read(CHUNK_SIZE):
            handle.write(chunk)
            digest.update(chunk)
            size += len(chunk)
            if progress and size >= next_report:
                progress(size, total)
                next_report += PROGRESS_STEP
    if progress:
        progress(size, size)
    return digest.hexdigest(), size


def _open(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(request, timeout=120)
