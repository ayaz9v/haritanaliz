"""Export the parts of the project config that the web app needs (config.json).

The web app never reads YAML. Each data version contains a ``config.json`` built from
config/settings.yaml and config/categories.yaml, so categories and zoom bands always match
the data they were produced with.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from haritanaliz.config import ProjectConfig

WEB_CONFIG_SCHEMA_VERSION = 1
WEB_CONFIG_FILE = "config.json"


def build_web_config(config: ProjectConfig) -> dict[str, Any]:
    categories = config.categories
    return {
        "schema_version": WEB_CONFIG_SCHEMA_VERSION,
        "zoom_bands": [band.model_dump(mode="json") for band in config.settings.map.zoom_bands],
        "boundary_levels": [
            level.model_dump(mode="json") for level in config.settings.map.boundary_levels
        ],
        "category_groups": [{"id": group.id, "name": group.name} for group in categories.groups],
        "categories": [
            {"id": category.id, "name": category.name, "group": category.group}
            for category in categories.categories
        ],
    }


def write_web_config(config: ProjectConfig, out_path: Path) -> Path:
    """Write config.json as UTF-8 with LF line endings and return its path."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(build_web_config(config), ensure_ascii=False, indent=2) + "\n"
    out_path.write_text(text, encoding="utf-8", newline="\n")
    return out_path
