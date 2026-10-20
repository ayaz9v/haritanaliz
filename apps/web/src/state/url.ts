import { REGION_ID_PATTERN } from "@/data/regions";
import { DEFAULT_FILTERS, isMetric, isMode, type Filters } from "./filters";

/** Query parameter names; every filter combination can be shared as a link. */
export const URL_PARAMS = {
  categories: "cat",
  metric: "metric",
  region: "region",
  mode: "mode",
} as const;

const CATEGORY_ID_PATTERN = /^[a-z][a-z0-9_]*$/;

/** Reads filters from a query string. Missing or invalid values are left out. */
export function filtersFromSearch(search: string): Partial<Filters> {
  const params = new URLSearchParams(search);
  const filters: Partial<Filters> = {};

  const categories = params.get(URL_PARAMS.categories);
  if (categories) {
    filters.categories = categories
      .split(",")
      .map((id) => id.trim())
      .filter((id) => CATEGORY_ID_PATTERN.test(id));
  }
  const metric = params.get(URL_PARAMS.metric);
  if (isMetric(metric)) filters.metric = metric;

  const region = params.get(URL_PARAMS.region);
  if (region && REGION_ID_PATTERN.test(region)) filters.regionId = region;

  const mode = params.get(URL_PARAMS.mode);
  if (isMode(mode)) filters.mode = mode;

  return filters;
}

/**
 * Builds the query string ("" or "?...") for `filters`. Parameters that do not belong to the
 * filters are kept; default values are left out so that shared links stay short.
 */
export function filtersToSearch(filters: Filters, currentSearch = ""): string {
  const ownKeys = new Set<string>(Object.values(URL_PARAMS));
  const parts: string[] = [];
  for (const [key, value] of new URLSearchParams(currentSearch)) {
    if (!ownKeys.has(key)) parts.push(`${encodeURIComponent(key)}=${encodeValue(value)}`);
  }

  const add = (key: string, value: string | null) => {
    if (value) parts.push(`${key}=${encodeValue(value)}`);
  };
  add(URL_PARAMS.categories, filters.categories.join(","));
  add(URL_PARAMS.metric, filters.metric === DEFAULT_FILTERS.metric ? null : filters.metric);
  add(URL_PARAMS.region, filters.regionId);
  add(URL_PARAMS.mode, filters.mode === DEFAULT_FILTERS.mode ? null : filters.mode);

  return parts.length > 0 ? `?${parts.join("&")}` : "";
}

/** encodeURIComponent, but commas stay readable in category lists. */
function encodeValue(value: string): string {
  return encodeURIComponent(value).replace(/%2C/gi, ",");
}
