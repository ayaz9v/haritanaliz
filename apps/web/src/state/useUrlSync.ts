import { useEffect } from "react";
import { pickFilters, type Filters } from "./filters";
import { useFilterStore } from "./store";
import { filtersFromSearch, filtersToSearch } from "./url";

function writeUrl(filters: Filters): void {
  const search = filtersToSearch(pickFilters(filters), window.location.search);
  if (search === window.location.search) return;
  // replaceState: individual filter clicks should not fill the back-button history.
  window.history.replaceState(
    window.history.state,
    "",
    `${window.location.pathname}${search}${window.location.hash}`,
  );
}

/**
 * Keeps the query string in sync with the filter store. The store reads the URL once at
 * start-up; from then on every change is written back. The map position lives in the hash
 * (`#map=zoom/lat/lng`), which MapLibre manages.
 */
export function useUrlSync(): void {
  useEffect(() => {
    // Rewrite the initial URL too, which drops invalid or default-valued parameters.
    writeUrl(useFilterStore.getState());
    const unsubscribe = useFilterStore.subscribe(writeUrl);

    const onPopState = () => {
      useFilterStore.getState().replaceFilters(filtersFromSearch(window.location.search));
    };
    window.addEventListener("popstate", onPopState);

    return () => {
      unsubscribe();
      window.removeEventListener("popstate", onPopState);
    };
  }, []);
}
