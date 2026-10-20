"""The sample data in apps/web/public/data-sample must follow the pipeline's contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from haritanaliz.config import ProjectConfig
from haritanaliz.manifest import Manifest
from haritanaliz.webconfig import build_web_config

SAMPLE_DIR = Path("apps") / "web" / "public" / "data-sample"


@pytest.fixture(scope="module")
def sample_dir(repo_root: Path) -> Path:
    return repo_root / SAMPLE_DIR


@pytest.fixture(scope="module")
def sample_manifest(sample_dir: Path) -> Manifest:
    return Manifest.model_validate_json((sample_dir / "manifest.json").read_text(encoding="utf-8"))


def _manifest_dict() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "latest": "2026-10-01",
        "versions": [
            {
                "version": "2026-10-01",
                "path": "v/2026-10-01/",
                "published_at": "2026-10-02T03:00:00Z",
                "files": {"config": "config.json"},
            }
        ],
    }


def test_sample_manifest_is_valid(sample_manifest: Manifest) -> None:
    assert sample_manifest.sample is True
    assert sample_manifest.latest_version().files["config"] == "config.json"


def test_sample_web_config_matches_config_files(
    sample_dir: Path, sample_manifest: Manifest, project_config: ProjectConfig
) -> None:
    latest = sample_manifest.latest_version()
    path = sample_dir / latest.path / latest.files["config"]
    sample = json.loads(path.read_text(encoding="utf-8"))
    assert sample == build_web_config(project_config), (
        "apps/web sample config.json is out of date. Regenerate it with:\n"
        f"  uv run haritanaliz export-web-config --out ../{SAMPLE_DIR.as_posix()}/"
        f"{latest.path}config.json"
    )


def test_manifest_accepts_minimal_release() -> None:
    manifest = Manifest.model_validate(_manifest_dict())
    assert manifest.sample is False
    assert manifest.latest_version().version == "2026-10-01"


def test_manifest_rejects_latest_missing_from_versions() -> None:
    data = _manifest_dict()
    data["latest"] = "2026-11-01"
    with pytest.raises(ValidationError, match="not listed"):
        Manifest.model_validate(data)


def test_manifest_rejects_path_for_another_version() -> None:
    data = _manifest_dict()
    data["versions"][0]["path"] = "v/2026-09-01/"
    with pytest.raises(ValidationError, match="does not end with"):
        Manifest.model_validate(data)


def test_manifest_rejects_impossible_dates() -> None:
    data = _manifest_dict()
    data["latest"] = data["versions"][0]["version"] = "2026-02-30"
    data["versions"][0]["path"] = "v/2026-02-30/"
    with pytest.raises(ValidationError):
        Manifest.model_validate(data)


def test_manifest_requires_newest_first() -> None:
    data = _manifest_dict()
    older = {**data["versions"][0], "version": "2026-09-01", "path": "v/2026-09-01/"}
    data["versions"] = [older, data["versions"][0]]
    with pytest.raises(ValidationError, match="newest first"):
        Manifest.model_validate(data)


def test_manifest_requires_timezone() -> None:
    data = _manifest_dict()
    data["versions"][0]["published_at"] = "2026-10-02T03:00:00"
    with pytest.raises(ValidationError, match="timezone"):
        Manifest.model_validate(data)
