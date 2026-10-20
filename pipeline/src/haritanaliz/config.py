"""Project configuration: config/settings.yaml and config/categories.yaml.

Both files are validated with pydantic. Unknown keys are rejected so that typos in YAML
fail loudly instead of silently falling back to defaults.
"""

from __future__ import annotations

import itertools
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal, Self

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
    model_validator,
)

SETTINGS_FILE = "settings.yaml"
CATEGORIES_FILE = "categories.yaml"

Identifier = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*$", max_length=64)]
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
OsmTagFilter = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_:]*=[a-z0-9_;:.\-]+$")]
OvertureCategory = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*$")]
HttpsUrl = Annotated[str, StringConstraints(pattern=r"^https://\S+$")]


class StrictModel(BaseModel):
    """Base model: unknown keys are errors and validated objects are immutable."""

    model_config = ConfigDict(extra="forbid", frozen=True)


# --------------------------------------------------------------------------------------
# settings.yaml
# --------------------------------------------------------------------------------------


class RegionSettings(StrictModel):
    country_code: Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]
    bbox: tuple[float, float, float, float]

    @field_validator("bbox")
    @classmethod
    def _check_bbox(
        cls, bbox: tuple[float, float, float, float]
    ) -> tuple[float, float, float, float]:
        lon_min, lat_min, lon_max, lat_max = bbox
        if not (-180 <= lon_min < lon_max <= 180 and -90 <= lat_min < lat_max <= 90):
            raise ValueError("bbox must be [lon_min, lat_min, lon_max, lat_max] with min < max")
        return bbox


class PathSettings(StrictModel):
    data_dir: Path
    raw_dir: Path
    interim_dir: Path
    output_dir: Path
    tuik_dir: Path
    osm_dir: Path

    @model_validator(mode="after")
    def _relative_to_repo(self) -> Self:
        for name, value in self:
            if value.anchor:
                raise ValueError(f"paths.{name} must be relative to the repository root")
        return self


class OvertureSource(StrictModel):
    release: Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}\.\d+$")] | None = None
    base_url: Annotated[str, StringConstraints(pattern=r"^(s3|https)://\S+$")]


class OsmSource(StrictModel):
    pbf_url: HttpsUrl


class TuikSource(StrictModel):
    adnks_year: int | None = Field(default=None, ge=2007, le=2100)


class SegeSource(StrictModel):
    year: int | None = Field(default=None, ge=2000, le=2100)


class SourceSettings(StrictModel):
    overture: OvertureSource
    osm: OsmSource
    tuik: TuikSource
    sege: SegeSource


class MatchingSettings(StrictModel):
    max_distance_m: float = Field(gt=0, le=1000)
    min_name_similarity: float = Field(ge=0, le=1)
    require_category_match: bool


class H3Settings(StrictModel):
    resolutions: list[Annotated[int, Field(ge=0, le=15)]] = Field(min_length=1)

    @field_validator("resolutions")
    @classmethod
    def _strictly_increasing(cls, values: list[int]) -> list[int]:
        if any(a >= b for a, b in itertools.pairwise(values)):
            raise ValueError("resolutions must be strictly increasing")
        return values


class SaturationSettings(StrictModel):
    surplus_threshold: float = Field(gt=0)
    deficit_threshold: float = Field(lt=0)


class OpportunityWeights(StrictModel):
    deficit: float = Field(ge=0, le=1)
    accessibility: float = Field(ge=0, le=1)
    demand: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _sum_to_one(self) -> Self:
        total = self.deficit + self.accessibility + self.demand
        if not math.isclose(total, 1.0, abs_tol=1e-9):
            raise ValueError(f"opportunity weights must sum to 1 (got {total:g})")
        return self


class ConfidenceSettings(StrictModel):
    high: float = Field(gt=0, le=1)
    medium: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if not self.medium < self.high:
            raise ValueError("confidence.medium must be lower than confidence.high")
        return self


class AnalysisSettings(StrictModel):
    min_population: int = Field(ge=0)
    overdispersion_alpha: float = Field(gt=0, lt=1)
    saturation: SaturationSettings
    opportunity_weights: OpportunityWeights
    confidence: ConfidenceSettings


IsoProvince = Annotated[str, StringConstraints(pattern=r"^TR-\d{2}$")]


class OfficialCounts(StrictModel):
    il: int = Field(gt=0)
    ilce: int = Field(gt=0)
    mahalle: int = Field(gt=0)
    koy: int = Field(gt=0)


class UrbanRadius(StrictModel):
    town: float = Field(gt=0, le=50)
    city: float = Field(gt=0, le=50)


class BoundarySettings(StrictModel):
    area_crs: Annotated[str, StringConstraints(pattern=r"^\+proj=")]
    country_iso: Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]
    min_parent_share: float = Field(gt=0, le=1)
    container_share: float = Field(gt=0, le=1)
    approx_place_values: list[Identifier] = Field(min_length=1)
    urban_radius_km: UrbanRadius
    duplicate_iou: float = Field(gt=0, le=1)
    min_gap_km2: float = Field(ge=0)
    metropolitan_provinces: list[IsoProvince]
    special_zone_patterns: list[str] = Field(min_length=1)
    official_counts: OfficialCounts

    @field_validator("special_zone_patterns")
    @classmethod
    def _valid_patterns(cls, patterns: list[str]) -> list[str]:
        for pattern in patterns:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(f"invalid regular expression {pattern!r}: {exc}") from exc
        return patterns

    @field_validator("metropolitan_provinces")
    @classmethod
    def _unique_provinces(cls, provinces: list[str]) -> list[str]:
        _require_unique(provinces, "metropolitan province")
        return provinces


class ZoomBand(StrictModel):
    """A zoom range [min_zoom, max_zoom) that switches map layers."""

    id: Identifier
    name: DisplayName
    min_zoom: int = Field(ge=0, le=24)
    max_zoom: int = Field(gt=0, le=24)

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if not self.min_zoom < self.max_zoom:
            raise ValueError("min_zoom must be lower than max_zoom")
        return self


class BoundaryLevel(StrictModel):
    """Zoom range [min_zoom, max_zoom) in which a boundary level is filled and clickable."""

    id: Literal["il", "ilce", "birim"]
    min_zoom: int = Field(ge=0, le=24)
    max_zoom: int = Field(gt=0, le=24)


def _check_contiguous(ranges: list[Any], label: str) -> None:
    if ranges[0].min_zoom != 0:
        raise ValueError(f"the first {label} must start at zoom 0")
    for previous, current in itertools.pairwise(ranges):
        if previous.max_zoom != current.min_zoom:
            raise ValueError(
                f"{label}s must be contiguous: '{previous.id}' ends at {previous.max_zoom}"
                f" but '{current.id}' starts at {current.min_zoom}"
            )
    for item in ranges:
        if not item.min_zoom < item.max_zoom:
            raise ValueError(f"{label} '{item.id}': min_zoom must be lower than max_zoom")
    _require_unique([item.id for item in ranges], f"{label} id")


class MapSettings(StrictModel):
    zoom_bands: list[ZoomBand] = Field(min_length=1)
    boundary_levels: list[BoundaryLevel] = Field(min_length=3, max_length=3)

    @field_validator("zoom_bands")
    @classmethod
    def _contiguous(cls, bands: list[ZoomBand]) -> list[ZoomBand]:
        _check_contiguous(bands, "zoom band")
        return bands

    @field_validator("boundary_levels")
    @classmethod
    def _ordered_levels(cls, levels: list[BoundaryLevel]) -> list[BoundaryLevel]:
        if [level.id for level in levels] != ["il", "ilce", "birim"]:
            raise ValueError("boundary_levels must be il, ilce, birim in this order")
        _check_contiguous(levels, "boundary level")
        return levels


class TileSettings(StrictModel):
    max_zoom: int = Field(ge=1, le=16)
    layer_min_zoom: dict[Literal["il", "ilce", "birim", "ozel_bolge"], int]
    label_min_zoom: dict[Literal["il", "ilce", "birim"], int]

    @model_validator(mode="after")
    def _within_range(self) -> Self:
        for name, zoom in {**self.layer_min_zoom, **self.label_min_zoom}.items():
            if not 0 <= zoom <= self.max_zoom:
                raise ValueError(f"min zoom of '{name}' must be between 0 and max_zoom")
        if set(self.layer_min_zoom) != {"il", "ilce", "birim", "ozel_bolge"}:
            raise ValueError("layer_min_zoom needs il, ilce, birim and ozel_bolge")
        if set(self.label_min_zoom) != {"il", "ilce", "birim"}:
            raise ValueError("label_min_zoom needs il, ilce and birim")
        return self


class R2Settings(StrictModel):
    bucket: (
        Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$")] | None
    ) = None
    public_base_url: HttpsUrl | None = None
    dev_base_url: HttpsUrl | None = None


class ArchiveSettings(StrictModel):
    provider: Literal["google_drive"]
    folder_id: str | None = None


class PublishSettings(StrictModel):
    versions_prefix: Annotated[str, StringConstraints(pattern=r"^[a-z0-9_-]+/$")]
    manifest_key: Annotated[str, StringConstraints(pattern=r"^[a-z0-9_-]+\.json$")]
    # Rolling back needs the previous version to still be live.
    keep_live_versions: int = Field(ge=2)
    r2: R2Settings
    archive: ArchiveSettings


class Settings(StrictModel):
    schema_version: Literal[1]
    region: RegionSettings
    paths: PathSettings
    sources: SourceSettings
    matching: MatchingSettings
    h3: H3Settings
    analysis: AnalysisSettings
    boundaries: BoundarySettings
    map: MapSettings
    tiles: TileSettings
    publish: PublishSettings


# --------------------------------------------------------------------------------------
# categories.yaml
# --------------------------------------------------------------------------------------


class CategoryGroup(StrictModel):
    id: Identifier
    name: DisplayName


class Brand(StrictModel):
    name: DisplayName
    aliases: list[DisplayName] = Field(default_factory=list)


class BrandSet(StrictModel):
    name: DisplayName
    verified: bool = False
    brands: list[Brand] = Field(min_length=1)


class BrandFilter(StrictModel):
    """Keep only POIs whose brand is (include) or is not (exclude) in a brand set."""

    include: Identifier | None = None
    exclude: Identifier | None = None

    @model_validator(mode="after")
    def _exactly_one(self) -> Self:
        if (self.include is None) == (self.exclude is None):
            raise ValueError("brand_set needs exactly one of 'include' or 'exclude'")
        return self

    @property
    def brand_set_id(self) -> str:
        # Exactly one of include/exclude is set (enforced by _exactly_one).
        return self.include or self.exclude or ""


class OvertureMapping(StrictModel):
    """Candidate Overture `basic_category` values and `taxonomy.hierarchy` levels."""

    basic_category: list[OvertureCategory] = Field(default_factory=list)
    taxonomy: list[OvertureCategory] = Field(default_factory=list)
    verified: bool = False

    @model_validator(mode="after")
    def _not_empty(self) -> Self:
        if not self.basic_category and not self.taxonomy:
            raise ValueError("overture mapping needs at least one basic_category or taxonomy value")
        return self


class Category(StrictModel):
    id: Identifier
    name: DisplayName
    group: Identifier
    osm: list[OsmTagFilter] = Field(min_length=1)
    overture: OvertureMapping
    brand_set: BrandFilter | None = None


class CategoriesConfig(StrictModel):
    schema_version: Literal[1]
    groups: list[CategoryGroup] = Field(min_length=1)
    brand_sets: dict[Identifier, BrandSet] = Field(default_factory=dict)
    categories: list[Category] = Field(min_length=1)

    @model_validator(mode="after")
    def _references(self) -> Self:
        _require_unique([group.id for group in self.groups], "group id")
        _require_unique([category.id for category in self.categories], "category id")

        group_ids = {group.id for group in self.groups}
        for category in self.categories:
            if category.group not in group_ids:
                raise ValueError(f"category '{category.id}' uses unknown group '{category.group}'")
            if category.brand_set and category.brand_set.brand_set_id not in self.brand_sets:
                raise ValueError(
                    f"category '{category.id}' uses unknown brand set "
                    f"'{category.brand_set.brand_set_id}'"
                )

        used_groups = {category.group for category in self.categories}
        unused = [group.id for group in self.groups if group.id not in used_groups]
        if unused:
            raise ValueError(f"groups without categories: {', '.join(unused)}")
        return self

    def unverified_overture_mappings(self) -> list[str]:
        """Ids of categories whose Overture mapping has not been verified with data yet."""
        return [category.id for category in self.categories if not category.overture.verified]

    def unverified_brand_sets(self) -> list[str]:
        return [set_id for set_id, brand_set in self.brand_sets.items() if not brand_set.verified]


def parse_osm_tag(tag_filter: str) -> tuple[str, str]:
    """Split an OSM tag filter such as ``amenity=restaurant`` into ``(key, value)``."""
    key, _, value = tag_filter.partition("=")
    return key, value


# --------------------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------------------


class ConfigError(Exception):
    """A configuration file is missing, is not valid YAML, or failed validation."""

    def __init__(self, path: Path, message: str) -> None:
        super().__init__(f"{path}: {message}")
        self.path = path


@dataclass(frozen=True)
class ProjectConfig:
    config_dir: Path
    settings: Settings
    categories: CategoriesConfig

    @property
    def root(self) -> Path:
        """Repository root: config/ lives directly under it."""
        return self.config_dir.resolve().parent

    def path(self, relative: Path) -> Path:
        """Resolve a repository-relative path from settings.paths."""
        return self.root / relative


def load_settings(path: Path) -> Settings:
    return _load_model(Settings, path)


def load_categories(path: Path) -> CategoriesConfig:
    return _load_model(CategoriesConfig, path)


def load_config(config_dir: Path) -> ProjectConfig:
    """Load and validate both config files from ``config_dir``."""
    return ProjectConfig(
        config_dir=config_dir,
        settings=load_settings(config_dir / SETTINGS_FILE),
        categories=load_categories(config_dir / CATEGORIES_FILE),
    )


def _load_model[M: BaseModel](model: type[M], path: Path) -> M:
    data = _read_yaml(path)
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(path, "validation failed\n" + _format_errors(exc)) from exc


def _read_yaml(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except FileNotFoundError as exc:
        raise ConfigError(path, "file not found") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(path, f"invalid YAML: {exc}") from exc


def _format_errors(exc: ValidationError) -> str:
    lines = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"]) or "<root>"
        lines.append(f"  - {location}: {error['msg']}")
    return "\n".join(lines)


def _require_unique(values: list[str], label: str) -> None:
    duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
    if duplicates:
        raise ValueError(f"duplicate {label}: {', '.join(duplicates)}")
