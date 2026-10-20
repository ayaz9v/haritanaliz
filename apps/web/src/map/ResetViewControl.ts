import type { IControl, Map as MapLibreMap } from "maplibre-gl";
import { FIT_PADDING, TURKEY_BOUNDS } from "./constants";

const LABEL = "Türkiye'nin tamamını göster";

// Lucide "house" icon (ISC license).
const ICON = `<svg xmlns="http://www.w3.org/2000/svg" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .709-1.528l7-6a2 2 0 0 1 2.582 0l7 6A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>`;

/** A map control button that zooms back out to the whole of Türkiye. */
export class ResetViewControl implements IControl {
  private container: HTMLDivElement | null = null;

  onAdd(map: MapLibreMap): HTMLElement {
    const container = document.createElement("div");
    container.className = "maplibregl-ctrl maplibregl-ctrl-group";

    const button = document.createElement("button");
    button.type = "button";
    button.className = "haritanaliz-ctrl-reset";
    button.title = LABEL;
    button.setAttribute("aria-label", LABEL);
    button.innerHTML = ICON;
    button.addEventListener("click", () => {
      map.fitBounds(TURKEY_BOUNDS, { padding: FIT_PADDING });
    });

    container.append(button);
    this.container = container;
    return container;
  }

  onRemove(): void {
    this.container?.remove();
    this.container = null;
  }
}
