import { create } from "zustand";

export type MapStatus = "loading" | "ready" | "error";
/** "webgl": the browser cannot create a WebGL2 context (required by MapLibre v6). */
export type MapError = "webgl" | "other";

interface UiState {
  /** Desktop: the filter side panel is visible. */
  panelOpen: boolean;
  /** Mobile: the bottom sheet is expanded. */
  sheetExpanded: boolean;
  zoom: number | null;
  mapStatus: MapStatus;
  mapError: MapError | null;
  togglePanel: () => void;
  setSheetExpanded: (expanded: boolean) => void;
  /** Brings the filter/analysis panel into view on both layouts. */
  revealPanel: () => void;
  setZoom: (zoom: number) => void;
  setMapReady: () => void;
  reportMapError: (error: MapError) => void;
}

/** Layout and map state that is not part of shareable links. */
export const useUiStore = create<UiState>()((set) => ({
  panelOpen: true,
  sheetExpanded: false,
  zoom: null,
  mapStatus: "loading",
  mapError: null,
  togglePanel: () => set((state) => ({ panelOpen: !state.panelOpen })),
  setSheetExpanded: (sheetExpanded) => set({ sheetExpanded }),
  revealPanel: () => set({ panelOpen: true, sheetExpanded: true }),
  setZoom: (zoom) => set({ zoom }),
  setMapReady: () => set({ mapStatus: "ready", mapError: null }),
  reportMapError: (mapError) => set({ mapStatus: "error", mapError }),
}));
