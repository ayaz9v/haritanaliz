import {
  DataFormatError,
  expectArray,
  expectNumber,
  expectRecord,
  expectString,
} from "@/lib/validate";

/**
 * config.json of a data version: categories and zoom bands, exported by the pipeline from
 * config/categories.yaml and config/settings.yaml (`haritanaliz export-web-config`).
 */
export interface WebConfig {
  schema_version: 1;
  zoom_bands: ZoomBand[];
  category_groups: CategoryGroup[];
  categories: Category[];
}

/** A zoom range [min_zoom, max_zoom) that switches map layers. */
export interface ZoomBand {
  id: string;
  name: string;
  min_zoom: number;
  max_zoom: number;
}

export interface CategoryGroup {
  id: string;
  name: string;
}

export interface Category {
  id: string;
  name: string;
  group: string;
}

const ID_PATTERN = /^[a-z][a-z0-9_]*$/;

export function parseWebConfig(input: unknown): WebConfig {
  const root = expectRecord(input, "config");
  if (root.schema_version !== 1) {
    throw new DataFormatError(`config: unsupported schema_version ${String(root.schema_version)}`);
  }

  const zoomBands = expectArray(root.zoom_bands, "config.zoom_bands").map((item, index) => {
    const where = `config.zoom_bands[${index}]`;
    const band = expectRecord(item, where);
    return {
      id: expectString(band.id, `${where}.id`, ID_PATTERN),
      name: expectString(band.name, `${where}.name`),
      min_zoom: expectNumber(band.min_zoom, `${where}.min_zoom`),
      max_zoom: expectNumber(band.max_zoom, `${where}.max_zoom`),
    };
  });

  const groups = expectArray(root.category_groups, "config.category_groups").map((item, index) => {
    const where = `config.category_groups[${index}]`;
    const group = expectRecord(item, where);
    return {
      id: expectString(group.id, `${where}.id`, ID_PATTERN),
      name: expectString(group.name, `${where}.name`),
    };
  });

  const groupIds = new Set(groups.map((group) => group.id));
  const categories = expectArray(root.categories, "config.categories").map((item, index) => {
    const where = `config.categories[${index}]`;
    const category = expectRecord(item, where);
    const parsed = {
      id: expectString(category.id, `${where}.id`, ID_PATTERN),
      name: expectString(category.name, `${where}.name`),
      group: expectString(category.group, `${where}.group`, ID_PATTERN),
    };
    if (!groupIds.has(parsed.group)) {
      throw new DataFormatError(`${where}: unknown group "${parsed.group}"`);
    }
    return parsed;
  });

  return { schema_version: 1, zoom_bands: zoomBands, category_groups: groups, categories };
}

/** The band that contains `zoom`; zooms past the last band belong to the last band. */
export function zoomBandAt(bands: readonly ZoomBand[], zoom: number): ZoomBand | undefined {
  const band = bands.find((item) => zoom >= item.min_zoom && zoom < item.max_zoom);
  if (band) return band;
  const last = bands.at(-1);
  return last && zoom >= last.max_zoom ? last : undefined;
}

export interface CategorySection {
  group: CategoryGroup;
  categories: Category[];
}

/** Categories grouped in the order of `category_groups`; empty groups are left out. */
export function groupCategories(
  config: Pick<WebConfig, "category_groups" | "categories">,
): CategorySection[] {
  return config.category_groups
    .map((group) => ({
      group,
      categories: config.categories.filter((category) => category.group === group.id),
    }))
    .filter((section) => section.categories.length > 0);
}
