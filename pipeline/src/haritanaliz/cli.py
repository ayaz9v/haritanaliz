"""Command line interface: ``haritanaliz <command>``.

The data commands (boundaries, pois, population, analyze, tiles, publish) are placeholders
and are implemented step by step; see docs/progress.md.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, NoReturn

import typer

from haritanaliz import __version__
from haritanaliz.config import ConfigError, ProjectConfig, load_config
from haritanaliz.paths import RepoRootNotFoundError, default_config_dir
from haritanaliz.webconfig import write_web_config

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


def _not_implemented(command: str) -> NoReturn:
    typer.echo(f"`haritanaliz {command}` is not implemented yet.", err=True)
    raise typer.Exit(code=1)


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


@app.command()
def boundaries() -> None:
    """Build province, district and neighbourhood/village boundaries (not implemented yet)."""
    _not_implemented("boundaries")


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
def tiles() -> None:
    """Build PMTiles with tippecanoe (not implemented yet)."""
    _not_implemented("tiles")


@app.command()
def publish() -> None:
    """Upload a data version to R2 and switch manifest.json (not implemented yet)."""
    _not_implemented("publish")
