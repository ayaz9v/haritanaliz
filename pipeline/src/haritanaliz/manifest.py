"""Data release manifest (manifest.json): the contract between the pipeline and the web app.

Every data refresh is published under ``v/YYYY-MM-DD/``. ``manifest.json`` lists the live
versions and names the one the site should use (``latest``). The manifest is uploaded last,
so switching to a new version is atomic, and rolling back only means pointing ``latest`` at
the previous version again. The web app validates the same structure in
``apps/web/src/data/manifest.ts``.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, Field, StringConstraints, field_validator, model_validator

from haritanaliz.config import StrictModel

MANIFEST_SCHEMA_VERSION = 1

VersionId = Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}$")]
FileKey = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*$")]
RelativeFile = Annotated[
    str, StringConstraints(pattern=r"^[A-Za-z0-9_\-]+(/[A-Za-z0-9_\-]+)*\.[a-z0-9]+$")
]
SourceId = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*$")]


class ManifestSource(StrictModel):
    """A data source in a version, e.g. an Overture release or the date of an OSM extract."""

    id: SourceId
    name: str
    version: str | None = None
    license: str | None = None


class ManifestVersion(StrictModel):
    version: VersionId
    path: Annotated[str, StringConstraints(pattern=r"^[a-z0-9_-]+/\d{4}-\d{2}-\d{2}/$")]
    published_at: AwareDatetime
    files: dict[FileKey, RelativeFile]
    sources: list[ManifestSource] = Field(default_factory=list)
    # Data licence of the version's files (ODbL for OSM-derived data, see K-037).
    license: str | None = None
    attribution: str | None = None

    @field_validator("version")
    @classmethod
    def _real_date(cls, value: str) -> str:
        date.fromisoformat(value)  # rejects impossible dates such as 2026-02-30
        return value

    @model_validator(mode="after")
    def _path_matches_version(self) -> Self:
        if not self.path.endswith(f"/{self.version}/"):
            raise ValueError(f"path '{self.path}' does not end with '/{self.version}/'")
        return self


class Manifest(StrictModel):
    schema_version: Literal[1]
    sample: bool = False
    latest: VersionId
    versions: list[ManifestVersion] = Field(min_length=1)

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        ids = [version.version for version in self.versions]
        if len(set(ids)) != len(ids):
            raise ValueError("versions must be unique")
        if ids != sorted(ids, reverse=True):
            raise ValueError("versions must be sorted newest first")
        if self.latest not in ids:
            raise ValueError(f"latest version {self.latest} is not listed in versions")
        return self

    def latest_version(self) -> ManifestVersion:
        return next(version for version in self.versions if version.version == self.latest)
