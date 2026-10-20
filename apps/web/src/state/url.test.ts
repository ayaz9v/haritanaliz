import { describe, expect, it } from "vitest";
import { DEFAULT_FILTERS, type Filters } from "./filters";
import { filtersFromSearch, filtersToSearch } from "./url";

describe("filtersFromSearch", () => {
  it("reads every filter", () => {
    expect(
      filtersFromSearch("?cat=pharmacy,cafe&metric=saturation&region=il-06&mode=opportunity"),
    ).toEqual({
      categories: ["pharmacy", "cafe"],
      metric: "saturation",
      regionId: "il-06",
      mode: "opportunity",
    });
  });

  it("ignores invalid values", () => {
    expect(
      filtersFromSearch("?cat=cafe,DROP%20TABLE,,eczane!&metric=best&region=<b>&mode=x"),
    ).toEqual({ categories: ["cafe"] });
  });

  it("returns nothing for an empty query", () => {
    expect(filtersFromSearch("")).toEqual({});
  });
});

describe("filtersToSearch", () => {
  it("leaves out default values", () => {
    expect(filtersToSearch(DEFAULT_FILTERS)).toBe("");
  });

  it("keeps foreign parameters and readable commas", () => {
    const filters: Filters = {
      ...DEFAULT_FILTERS,
      categories: ["cafe", "pharmacy"],
      regionId: "il-06",
    };
    expect(filtersToSearch(filters, "?utm_source=x&cat=old")).toBe(
      "?utm_source=x&cat=cafe,pharmacy&region=il-06",
    );
  });

  it("round-trips through the URL", () => {
    const filters: Filters = {
      categories: ["bakery"],
      metric: "count",
      regionId: "il-35",
      mode: "opportunity",
    };
    expect(filtersFromSearch(filtersToSearch(filters))).toEqual(filters);
  });
});
