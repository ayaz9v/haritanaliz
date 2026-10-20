import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { DEFAULT_FILTERS } from "./filters";
import { useFilterStore } from "./store";
import { useUrlSync } from "./useUrlSync";

beforeEach(() => {
  useFilterStore.setState(DEFAULT_FILTERS);
  window.history.replaceState(null, "", "/");
});

describe("useUrlSync", () => {
  it("writes filter changes to the query string and keeps the map hash", () => {
    window.history.replaceState(null, "", "/?utm_source=x#map=5/39/35");
    const { unmount } = renderHook(() => useUrlSync());

    act(() => {
      useFilterStore.getState().toggleCategory("cafe");
      useFilterStore.getState().setRegion("il-06");
    });

    expect(window.location.search).toBe("?utm_source=x&cat=cafe&region=il-06");
    expect(window.location.hash).toBe("#map=5/39/35");
    unmount();
  });

  it("drops invalid parameters from the initial URL", () => {
    window.history.replaceState(null, "", "/?metric=nonsense&cat=cafe");
    useFilterStore.getState().replaceFilters({ categories: ["cafe"] });
    const { unmount } = renderHook(() => useUrlSync());
    expect(window.location.search).toBe("?cat=cafe");
    unmount();
  });

  it("applies the URL on back/forward navigation", () => {
    const { unmount } = renderHook(() => useUrlSync());
    act(() => {
      window.history.replaceState(null, "", "/?cat=bakery&mode=opportunity");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    expect(useFilterStore.getState()).toMatchObject({
      categories: ["bakery"],
      mode: "opportunity",
    });
    unmount();
  });
});
