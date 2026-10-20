"""Command line interface: ``haritanaliz <command>``.

Implemented: validate-config, export-web-config, download-osm, boundaries, tiles, sample.
The other data commands (pois, population, analyze, publish) are placeholders that come in
later steps; see docs/progress.md.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, NoReturn

import typer

from haritanaliz import __version__
from haritanaliz.config import ConfigError, ProjectConfig, load_config
from haritanaliz.paths import RepoRootNotFoundError, default_config_dir
from haritanaliz.webconfig import WEB_CONFIG_FILE, write_web_config

if TYPE_CHECKING:
    from haritanaliz.osm.download import OsmExtract

app = typer.Typer(
    name="haritanaliz",
    help="haritanaliz data and analysis pipeline.",
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)

ConfigDirOption = Annotated[
    Path | None,
    typer.Option(
        "--config-dir",
        help="Folder that contains settings.yaml and categories.yaml [default: <repo>/config].",
        file_okay=False,
    ),
]
OsmDateOption = Annotated[
    str | None,
    typer.Option(
        "--osm-date",
        help="Data date of the OSM extract, YYYY-MM-DD [default: latest downloaded].",
    ),
]
BOUNDARY_TILES = "boundaries.pmtiles"


def _show_version(value: bool) -> None:
    if value:
        typer.echo(f"haritanaliz {__version__}")
        raise typer.Exit


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version", callback=_show_version, is_eager=True, help="Show the version and exit."
        ),
    ] = False,
) -> None:
    """haritanaliz data and analysis pipeline."""


def _load(config_dir: Path | None) -> ProjectConfig:
    try:
        return load_config(config_dir if config_dir is not None else default_config_dir())
    except (ConfigError, RepoRootNotFoundError) as exc:
        typer.echo(f"Configuration error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


def _fail(message: str) -> NoReturn:
    typer.echo(message, err=True)
    raise typer.Exit(code=1)


def _not_implemented(command: str) -> NoReturn:
    _fail(f"`haritanaliz {command}` is not implemented yet.")


def _extract(config: ProjectConfig, osm_date: str | None) -> OsmExtract:
    from haritanaliz.osm.download import find_extract

    extract = find_extract(config.path(config.settings.paths.osm_dir), osm_date)
    if extract is None:
        _fail("No OSM extract found. Run `haritanaliz download-osm` first.")
    return extract


def _site_dir(config: ProjectConfig) -> Path:
    return config.path(config.settings.paths.output_dir) / "site"


@app.command("validate-config")
def validate_config(config_dir: ConfigDirOption = None) -> None:
    """Validate config/settings.yaml and config/categories.yaml."""
    config = _load(config_dir)
    settings, categories = config.settings, config.categories
    typer.echo(f"Configuration is valid: {config.config_dir}")
    typer.echo(
        f"  settings.yaml: {len(settings.map.zoom_bands)} zoom bands, "
        f"H3 resolutions {settings.h3.resolutions}"
    )
    typer.echo(
        f"  categories.yaml: {len(categories.categories)} categories in "
        f"{len(categories.groups)} groups, {len(categories.brand_sets)} brand set(s)"
    )
    unverified = categories.unverified_overture_mappings()
    if unverified:
        typer.echo(
            f"  note: Overture mappings not verified with data yet: "
            f"{len(unverified)}/{len(categories.categories)} categories"
        )
    unverified_sets = categories.unverified_brand_sets()
    if unverified_sets:
        typer.echo(f"  note: brand sets not verified with data yet: {', '.join(unverified_sets)}")


@app.command("export-web-config")
def export_web_config(
    out: Annotated[
        Path, typer.Option("--out", help="Output file, e.g. <version dir>/config.json.")
    ],
    config_dir: ConfigDirOption = None,
) -> None:
    """Write the web app config (categories, zoom bands) as JSON."""
    config = _load(config_dir)
    path = write_web_config(config, out)
    typer.echo(f"Wrote {path}")


@app.command("download-osm")
def download_osm(
    day: Annotated[
        str | None,
        typer.Option(
            "--date",
            help="Download Geofabrik's dated copy for this data date (YYYY-MM-DD) "
            "instead of the latest extract.",
        ),
    ] = None,
    config_dir: ConfigDirOption = None,
) -> None:
    """Download the Geofabrik Türkiye extract (MD5-verified) into paths.osm_dir."""
    from haritanaliz.osm.download import DownloadError, dated_url, download_extract

    config = _load(config_dir)
    url = config.settings.sources.osm.pbf_url
    if day is not None:
        url = dated_url(url, date.fromisoformat(day))
    osm_dir = config.path(config.settings.paths.osm_dir)

    def progress(done: int, total: int | None) -> None:
        share = f" ({done / total:.0%})" if total else ""
        typer.echo(f"  {done / 1024**2:,.0f} MB{share}", err=True)

    typer.echo(f"Checking {url}")
    try:
        extract, downloaded = download_extract(url, osm_dir, progress)
    except (DownloadError, OSError) as exc:
        _fail(f"Download failed: {exc}")
    state = "Downloaded" if downloaded else "Already up to date"
    typer.echo(f"{state}: {extract.path}")
    typer.echo(f"  md5 {extract.md5}, OSM data timestamp {extract.timestamp:%Y-%m-%dT%H:%M:%SZ}")


@app.command()
def boundaries(
    osm_date: OsmDateOption = None,
    report_dir: Annotated[
        Path | None,
        typer.Option("--report-dir", help="Quality report folder [default: <repo>/docs/reports]."),
    ] = None,
    config_dir: ConfigDirOption = None,
) -> None:
    """Build province, district and neighbourhood/village boundaries from the OSM extract.

    Writes the build (GeoParquet) to paths.interim_dir, the region files and manifest to
    <paths.output_dir>/site, tile input for `haritanaliz tiles`, and the quality report.
    """
    from haritanaliz.boundaries.build import build_boundaries
    from haritanaliz.boundaries.report import load_reference, render_report, write_tables
    from haritanaliz.boundaries.store import save_build
    from haritanaliz.boundaries.web import write_regions, write_tile_input
    from haritanaliz.osm.extract import (
        extract_boundaries,
        extract_is_cached,
        read_extract,
        write_extract,
    )
    from haritanaliz.site import osm_source, version_dir, write_manifest

    config = _load(config_dir)
    settings = config.settings
    extract_meta = _extract(config, osm_date)
    version = extract_meta.date
    interim = config.path(settings.paths.interim_dir)

    cache = interim / "osm" / version
    if not extract_is_cached(cache):
        typer.echo(f"Reading {extract_meta.path.name} with pyosmium...")
        write_extract(extract_boundaries(extract_meta.path, progress=typer.echo), cache)
    typer.echo("Building boundaries...")
    build = build_boundaries(read_extract(cache), settings.boundaries, log=typer.echo)
    save_build(build, interim / "boundaries" / version)

    site = _site_dir(config)
    folder = version_dir(site, version)
    write_web_config(config, folder / WEB_CONFIG_FILE)
    write_regions(build, folder)
    features = write_tile_input(
        build, interim / "tiles" / version / "boundaries.geojsonseq", settings.tiles
    )
    write_manifest(site, version, [osm_source(f"{extract_meta.timestamp:%Y-%m-%dT%H:%M:%SZ}")])

    reports = report_dir or config.root / "docs" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    reference = load_reference(config.config_dir / "reference" / "ilceler.json")
    report = render_report(
        build, extract_meta, settings.boundaries, reference, datetime.now(UTC).date()
    )
    (reports / "sinir_kalitesi.md").write_text(report, encoding="utf-8", newline="\n")
    write_tables(build, reports)

    counts = build.units.groupby(["type", "approx"]).size().to_dict()
    typer.echo(f"Provinces {len(build.provinces)}, districts {len(build.districts)}")
    typer.echo(f"Units by (type, approximate): {counts}")
    typer.echo(f"Site data: {folder}")
    typer.echo(f"Tile input: {features:,} features; next: `haritanaliz tiles`")
    typer.echo(f"Report: {reports / 'sinir_kalitesi.md'}")


@app.command()
def tiles(osm_date: OsmDateOption = None, config_dir: ConfigDirOption = None) -> None:
    """Build boundaries.pmtiles with tippecanoe (Linux/WSL or the GitHub workflow)."""
    from haritanaliz.site import osm_source, version_dir, write_manifest
    from haritanaliz.tiles import TippecanoeMissingError, build_tiles

    config = _load(config_dir)
    extract_meta = _extract(config, osm_date)
    version = extract_meta.date
    source = config.path(config.settings.paths.interim_dir) / "tiles" / version
    if not (source / "boundaries.geojsonseq").is_file():
        _fail("No tile input. Run `haritanaliz boundaries` first.")
    site = _site_dir(config)
    try:
        target = build_tiles(
            source / "boundaries.geojsonseq",
            version_dir(site, version) / BOUNDARY_TILES,
            config.settings.tiles,
            name="haritanaliz sınırlar",
        )
    except TippecanoeMissingError as exc:
        _fail(str(exc))
    write_manifest(site, version, [osm_source(f"{extract_meta.timestamp:%Y-%m-%dT%H:%M:%SZ}")])
    typer.echo(f"Wrote {target} ({target.stat().st_size / 1024**2:,.1f} MB)")


@app.command()
def sample(
    province: Annotated[
        str, typer.Option("--province", help="Plate code of the sample province.")
    ] = "35",
    out: Annotated[
        Path | None,
        typer.Option(
            "--out", help="Sample site folder [default: <repo>/apps/web/public/data-sample]."
        ),
    ] = None,
    osm_date: OsmDateOption = None,
    config_dir: ConfigDirOption = None,
) -> None:
    """Write the small sample data release used by the web app and its tests.

    All provinces and districts, plus the neighbourhoods/villages of one province. Tiles are
    built when tippecanoe is available (otherwise the sample has no boundaries.pmtiles).
    """
    import shutil

    from haritanaliz.boundaries.store import load_build, only_province, subset_province
    from haritanaliz.boundaries.web import write_regions, write_tile_input
    from haritanaliz.site import osm_source, version_dir, write_manifest
    from haritanaliz.tiles import TippecanoeMissingError, build_tiles

    config = _load(config_dir)
    extract_meta = _extract(config, osm_date)
    version = extract_meta.date
    interim = config.path(config.settings.paths.interim_dir)
    build = subset_province(load_build(interim / "boundaries" / version), province)

    site = out or config.root / "apps" / "web" / "public" / "data-sample"
    if (site / "v").is_dir():
        shutil.rmtree(site / "v")
    folder = version_dir(site, version)
    write_web_config(config, folder / WEB_CONFIG_FILE)
    write_regions(build, folder)
    tile_input = interim / "tiles" / version / f"sample-{province}.geojsonseq"
    write_tile_input(only_province(build, province), tile_input, config.settings.tiles)
    try:
        build_tiles(
            tile_input, folder / BOUNDARY_TILES, config.settings.tiles, name="haritanaliz örnek"
        )
    except TippecanoeMissingError:
        typer.echo("tippecanoe not found: the sample has no boundary tiles.", err=True)
    write_manifest(
        site, version, [osm_source(f"{extract_meta.timestamp:%Y-%m-%dT%H:%M:%SZ}")], sample=True
    )
    typer.echo(f"Sample written to {folder}")


@app.command()
def pois() -> None:
    """Extract and conflate businesses from Overture and OSM (not implemented yet)."""
    _not_implemented("pois")


@app.command()
def population() -> None:
    """Load TÜİK ADNKS population and SEGE indicators (not implemented yet)."""
    _not_implemented("population")


@app.command()
def analyze() -> None:
    """Compute indicators, count models and scores (not implemented yet)."""
    _not_implemented("analyze")


@app.command()
def publish() -> None:
    """Upload a data version to R2 and switch manifest.json (not implemented yet)."""
    _not_implemented("publish")
