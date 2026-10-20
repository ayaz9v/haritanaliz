from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from haritanaliz import __version__
from haritanaliz.cli import app

runner = CliRunner()

PLACEHOLDER_COMMANDS = ["pois", "population", "analyze", "publish"]
DATA_COMMANDS = ["download-osm", "boundaries", "tiles", "sample", *PLACEHOLDER_COMMANDS]


def test_help_lists_all_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in [*DATA_COMMANDS, "validate-config", "export-web-config"]:
        assert command in result.output


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_validate_config_accepts_repository_config(config_dir: Path) -> None:
    result = runner.invoke(app, ["validate-config", "--config-dir", str(config_dir)])
    assert result.exit_code == 0, result.output
    assert "Configuration is valid" in result.output
    assert "23 categories in 6 groups" in result.output


def test_validate_config_reports_errors(
    write_config, settings_data: dict[str, Any], categories_data: dict[str, Any]
) -> None:
    settings_data["map"]["zoom_bands"][0]["min_zoom"] = 3
    directory = write_config(settings_data, categories_data)
    result = runner.invoke(app, ["validate-config", "--config-dir", str(directory)])
    assert result.exit_code == 1
    assert "Configuration error" in result.output
    assert "zoom 0" in result.output


@pytest.mark.parametrize("command", PLACEHOLDER_COMMANDS)
def test_later_commands_are_placeholders(command: str) -> None:
    result = runner.invoke(app, [command])
    assert result.exit_code == 1
    assert "not implemented yet" in result.output


@pytest.mark.parametrize("command", ["boundaries", "tiles", "sample"])
def test_boundary_commands_need_a_downloaded_extract(
    command: str, write_config, settings_data: dict[str, Any], categories_data: dict[str, Any]
) -> None:
    directory = write_config(settings_data, categories_data)
    result = runner.invoke(app, [command, "--config-dir", str(directory)])
    assert result.exit_code == 1
    assert "download-osm" in result.output


def test_export_web_config_writes_json(config_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "nested" / "config.json"
    result = runner.invoke(
        app, ["export-web-config", "--config-dir", str(config_dir), "--out", str(out)]
    )
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert len(data["categories"]) == 23
    assert b"\r\n" not in out.read_bytes()
