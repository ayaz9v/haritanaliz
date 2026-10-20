from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from haritanaliz.config import (
    CategoriesConfig,
    ConfigError,
    ProjectConfig,
    Settings,
    load_config,
    parse_osm_tag,
)

# The 23 starting categories from the project definition (CLAUDE.md).
INITIAL_CATEGORY_IDS = {
    "restaurant",
    "cafe",
    "fast_food",
    "pastry",
    "bakery",
    "supermarket",
    "chain_market",
    "convenience",
    "butcher",
    "greengrocer",
    "pharmacy",
    "hairdresser",
    "car_parts",
    "car_repair",
    "fuel",
    "clothes",
    "electronics",
    "mobile_phone",
    "appliance",
    "stationery",
    "gym",
    "veterinary",
    "dentist",
}


def _category(data: dict[str, Any], category_id: str) -> dict[str, Any]:
    return next(item for item in data["categories"] if item["id"] == category_id)


# --- the real config files ---------------------------------------------------------------


def test_repository_config_is_valid(project_config: ProjectConfig) -> None:
    assert project_config.settings.schema_version == 1
    assert project_config.categories.schema_version == 1


def test_initial_categories_are_present(project_config: ProjectConfig) -> None:
    ids = [category.id for category in project_config.categories.categories]
    assert len(ids) == 23
    assert set(ids) == INITIAL_CATEGORY_IDS


def test_every_category_has_osm_tags_and_overture_candidates(
    project_config: ProjectConfig,
) -> None:
    for category in project_config.categories.categories:
        assert category.osm, category.id
        assert category.overture.basic_category or category.overture.taxonomy, category.id


def test_overture_mappings_are_marked_unverified_until_step_2(
    project_config: ProjectConfig,
) -> None:
    assert project_config.categories.unverified_overture_mappings() == [
        category.id for category in project_config.categories.categories
    ]


def test_chain_markets_are_separated_by_brand(project_config: ProjectConfig) -> None:
    by_id = {category.id: category for category in project_config.categories.categories}
    assert by_id["chain_market"].brand_set is not None
    assert by_id["chain_market"].brand_set.include == "discount_chains"
    for category_id in ("supermarket", "convenience"):
        brand_filter = by_id[category_id].brand_set
        assert brand_filter is not None
        assert brand_filter.exclude == "discount_chains"
    brands = {
        brand.name for brand in project_config.categories.brand_sets["discount_chains"].brands
    }
    assert {"BİM", "A101", "ŞOK"} <= brands


def test_parse_osm_tag() -> None:
    assert parse_osm_tag("amenity=restaurant") == ("amenity", "restaurant")
    assert parse_osm_tag("healthcare=dentist") == ("healthcare", "dentist")


# --- settings.yaml rules -----------------------------------------------------------------


def test_opportunity_weights_must_sum_to_one(settings_data: dict[str, Any]) -> None:
    settings_data["analysis"]["opportunity_weights"]["demand"] = 0.5
    with pytest.raises(ValidationError, match="sum to 1"):
        Settings.model_validate(settings_data)


def test_saturation_thresholds_need_correct_signs(settings_data: dict[str, Any]) -> None:
    settings_data["analysis"]["saturation"]["deficit_threshold"] = 1.0
    with pytest.raises(ValidationError, match="deficit_threshold"):
        Settings.model_validate(settings_data)


def test_zoom_bands_must_be_contiguous(settings_data: dict[str, Any]) -> None:
    settings_data["map"]["zoom_bands"][1]["min_zoom"] = 10
    with pytest.raises(ValidationError, match="contiguous"):
        Settings.model_validate(settings_data)


def test_rollback_needs_two_live_versions(settings_data: dict[str, Any]) -> None:
    settings_data["publish"]["keep_live_versions"] = 1
    with pytest.raises(ValidationError, match="keep_live_versions"):
        Settings.model_validate(settings_data)


def test_bbox_must_be_ordered(settings_data: dict[str, Any]) -> None:
    settings_data["region"]["bbox"] = [44.9, 35.7, 25.5, 42.2]
    with pytest.raises(ValidationError, match="bbox"):
        Settings.model_validate(settings_data)


def test_absolute_data_paths_are_rejected(settings_data: dict[str, Any]) -> None:
    settings_data["paths"]["data_dir"] = "/tmp/data"
    with pytest.raises(ValidationError, match="relative"):
        Settings.model_validate(settings_data)


def test_unknown_keys_are_rejected(settings_data: dict[str, Any]) -> None:
    settings_data["analysis"]["opportunity_weigths"] = {}  # typo must not be ignored
    with pytest.raises(ValidationError, match="opportunity_weigths"):
        Settings.model_validate(settings_data)


# --- categories.yaml rules ---------------------------------------------------------------


def test_unknown_group_is_rejected(categories_data: dict[str, Any]) -> None:
    _category(categories_data, "cafe")["group"] = "drinks"
    with pytest.raises(ValidationError, match="unknown group 'drinks'"):
        CategoriesConfig.model_validate(categories_data)


def test_duplicate_category_ids_are_rejected(categories_data: dict[str, Any]) -> None:
    _category(categories_data, "bakery")["id"] = "cafe"
    with pytest.raises(ValidationError, match="duplicate category id: cafe"):
        CategoriesConfig.model_validate(categories_data)


def test_malformed_osm_tag_is_rejected(categories_data: dict[str, Any]) -> None:
    _category(categories_data, "cafe")["osm"] = ["amenity cafe"]
    with pytest.raises(ValidationError, match="osm"):
        CategoriesConfig.model_validate(categories_data)


def test_unknown_brand_set_is_rejected(categories_data: dict[str, Any]) -> None:
    _category(categories_data, "chain_market")["brand_set"] = {"include": "hard_discount"}
    with pytest.raises(ValidationError, match="unknown brand set 'hard_discount'"):
        CategoriesConfig.model_validate(categories_data)


def test_brand_filter_needs_exactly_one_mode(categories_data: dict[str, Any]) -> None:
    _category(categories_data, "chain_market")["brand_set"] = {
        "include": "discount_chains",
        "exclude": "discount_chains",
    }
    with pytest.raises(ValidationError, match="exactly one"):
        CategoriesConfig.model_validate(categories_data)


def test_unused_group_is_rejected(categories_data: dict[str, Any]) -> None:
    categories_data["groups"].append({"id": "education", "name": "Eğitim"})
    with pytest.raises(ValidationError, match="groups without categories: education"):
        CategoriesConfig.model_validate(categories_data)


def test_empty_overture_mapping_is_rejected(categories_data: dict[str, Any]) -> None:
    _category(categories_data, "cafe")["overture"] = {"verified": False}
    with pytest.raises(ValidationError, match="at least one"):
        CategoriesConfig.model_validate(categories_data)


# --- loading -----------------------------------------------------------------------------


def test_load_config_reports_file_and_field(
    write_config, settings_data: dict[str, Any], categories_data: dict[str, Any]
) -> None:
    settings_data["analysis"]["opportunity_weights"]["deficit"] = 0.9
    directory = write_config(settings_data, categories_data)
    with pytest.raises(ConfigError) as excinfo:
        load_config(directory)
    message = str(excinfo.value)
    assert "settings.yaml" in message
    assert "analysis.opportunity_weights" in message


def test_missing_config_file_raises_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="file not found"):
        load_config(tmp_path)


def test_invalid_yaml_raises_config_error(
    write_config, settings_data: dict[str, Any], categories_data: dict[str, Any]
) -> None:
    directory = write_config(settings_data, categories_data)
    (directory / "categories.yaml").write_text("groups: [unclosed", encoding="utf-8")
    with pytest.raises(ConfigError, match="invalid YAML"):
        load_config(directory)
