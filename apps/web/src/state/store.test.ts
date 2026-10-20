import { beforeEach, describe, expect, it } from "vitest";
import { DEFAULT_FILTERS } from "./filters";
import { useFilterStore } from "./store";

const state = () => useFilterStore.getState();

beforeEach(() => {
  useFilterStore.setState(DEFAULT_FILTERS);
});

describe("filter store", () => {
  it("toggles categories and keeps them sorted", () => {
    state().toggleCategory("pharmacy");
    state().toggleCategory("cafe");
    expect(state().categories).toEqual(["cafe", "pharmacy"]);
    state().toggleCategory("pharmacy");
    expect(state().categories).toEqual(["cafe"]);
  });

  it("allows a single category in opportunity mode", () => {
    state().toggleCategory("cafe");
    state().toggleCategory("pharmacy");
    state().setMode("opportunity");
    expect(state().categories).toEqual(["cafe"]);
    state().toggleCategory("bakery");
    expect(state().categories).toEqual(["bakery"]);
  });

  it("normalizes replaced filters and falls back to defaults", () => {
    state().setMetric("count");
    state().replaceFilters({ categories: ["pharmacy", "cafe", "cafe"], regionId: "il-06" });
    expect(state()).toMatchObject({
      categories: ["cafe", "pharmacy"],
      regionId: "il-06",
      metric: DEFAULT_FILTERS.metric,
      mode: "explore",
    });
  });
});
