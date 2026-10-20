from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

from haritanaliz.config import CATEGORIES_FILE, SETTINGS_FILE, ProjectConfig, load_config
from haritanaliz.paths import find_repo_root


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return find_repo_root(Path(__file__).parent)


@pytest.fixture(scope="session")
def config_dir(repo_root: Path) -> Path:
    return repo_root / "config"


@pytest.fixture(scope="session")
def project_config(config_dir: Path) -> ProjectConfig:
    return load_config(config_dir)


@pytest.fixture(scope="session")
def _raw_settings(config_dir: Path) -> dict[str, Any]:
    return yaml.safe_load((config_dir / SETTINGS_FILE).read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def _raw_categories(config_dir: Path) -> dict[str, Any]:
    return yaml.safe_load((config_dir / CATEGORIES_FILE).read_text(encoding="utf-8"))


@pytest.fixture
def settings_data(_raw_settings: dict[str, Any]) -> dict[str, Any]:
    """A mutable copy of the real settings.yaml, for negative tests."""
    return copy.deepcopy(_raw_settings)


@pytest.fixture
def categories_data(_raw_categories: dict[str, Any]) -> dict[str, Any]:
    """A mutable copy of the real categories.yaml, for negative tests."""
    return copy.deepcopy(_raw_categories)


@pytest.fixture
def write_config(tmp_path: Path):
    """Write settings/categories dicts as YAML into a temporary config folder."""

    def _write(settings: dict[str, Any], categories: dict[str, Any]) -> Path:
        directory = tmp_path / "config"
        directory.mkdir(exist_ok=True)
        for name, data in ((SETTINGS_FILE, settings), (CATEGORIES_FILE, categories)):
            (directory / name).write_text(
                yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
            )
        return directory

    return _write
