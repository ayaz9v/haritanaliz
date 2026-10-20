import { create } from "zustand";
import { DEFAULT_FILTERS, normalizeFilters, type Filters, type Metric, type Mode } from "./filters";
import { filtersFromSearch } from "./url";

interface FilterActions {
  toggleCategory: (id: string) => void;
  clearCategories: () => void;
  setMetric: (metric: Metric) => void;
  setRegion: (regionId: string | null) => void;
  setMode: (mode: Mode) => void;
  /** Replaces every filter; missing fields fall back to the defaults (used on URL changes). */
  replaceFilters: (filters: Partial<Filters>) => void;
}

export type FilterStore = Filters & FilterActions;

function initialFilters(): Filters {
  const fromUrl = typeof window === "undefined" ? {} : filtersFromSearch(window.location.search);
  return normalizeFilters({ ...DEFAULT_FILTERS, ...fromUrl });
}

/** Filter state. useUrlSync mirrors it to the query string so that views can be shared. */
export const useFilterStore = create<FilterStore>()((set) => ({
  ...initialFilters(),

  toggleCategory: (id) =>
    set((state) => {
      if (state.categories.includes(id)) {
        return { categories: state.categories.filter((category) => category !== id) };
      }
      // Opportunity mode ranks neighbourhoods for a single business type.
      if (state.mode === "opportunity") return { categories: [id] };
      return { categories: [...state.categories, id].sort() };
    }),

  clearCategories: () => set({ categories: [] }),

  setMetric: (metric) => set({ metric }),

  setRegion: (regionId) => set({ regionId }),

  setMode: (mode) =>
    set((state) => ({
      mode,
      categories: mode === "opportunity" ? state.categories.slice(0, 1) : state.categories,
    })),

  replaceFilters: (filters) => set(normalizeFilters({ ...DEFAULT_FILTERS, ...filters })),
}));
