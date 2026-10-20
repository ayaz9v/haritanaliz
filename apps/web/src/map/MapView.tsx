import "maplibre-gl/dist/maplibre-gl.css";
import {
  GPUInitializationError,
  Map as MapLibreMap,
  NavigationControl,
  ScaleControl,
} from "maplibre-gl";
import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import { useUiStore, type MapError } from "@/state/ui";
import { BASEMAP_STYLE_URL, FIT_PADDING, MAP_LOCALE_TR, TURKEY_BOUNDS } from "./constants";
import { applyTurkishLabels } from "./labels";
import { setupMapLibre } from "./maplibre";
import { ResetViewControl } from "./ResetViewControl";

const ERROR_MESSAGES: Record<MapError, string> = {
  webgl:
    "Harita gösterilemiyor: tarayıcınız WebGL2 desteklemiyor ya da kapalı. Güncel bir tarayıcıyla tekrar deneyin.",
  other: "Harita yüklenemedi. Sayfayı yenileyip tekrar deneyin.",
};

/**
 * The MapLibre map. Opens on the whole of Türkiye unless the URL hash (`#map=z/lat/lng`)
 * holds a position; zooming and panning are free.
 */
export function MapView({ className }: { className?: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const status = useUiStore((state) => state.mapStatus);
  const error = useUiStore((state) => state.mapError);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    // The map is an external system; its state reaches React through the UI store.
    const { setMapReady, reportMapError, setZoom } = useUiStore.getState();
    setupMapLibre();

    let map: MapLibreMap;
    try {
      map = new MapLibreMap({
        container,
        style: BASEMAP_STYLE_URL,
        bounds: TURKEY_BOUNDS,
        fitBoundsOptions: { padding: FIT_PADDING },
        hash: "map",
        locale: MAP_LOCALE_TR,
        // The attribution bar under the map is always visible instead.
        attributionControl: false,
        dragRotate: false,
        pitchWithRotate: false,
        touchPitch: false,
        maxPitch: 0,
        minZoom: 3,
      });
    } catch (cause) {
      console.error(cause);
      reportMapError(cause instanceof GPUInitializationError ? "webgl" : "other");
      return;
    }

    map.on("style.load", () => applyTurkishLabels(map));
    map.touchZoomRotate.disableRotation();
    map.addControl(new NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new ResetViewControl(), "top-right");
    map.addControl(new ScaleControl({ unit: "metric" }), "bottom-left");

    const syncZoom = () => setZoom(map.getZoom());
    map.on("zoomend", syncZoom);
    map.once("load", () => {
      syncZoom();
      setMapReady();
    });

    return () => map.remove();
  }, []);

  return (
    <div className={cn("absolute", className)}>
      <div ref={containerRef} className="size-full" data-map-status={status} />
      {status === "error" && (
        <div
          role="alert"
          className="absolute inset-0 grid place-items-center bg-muted p-6 text-center text-sm text-muted-foreground"
        >
          {ERROR_MESSAGES[error ?? "other"]}
        </div>
      )}
    </div>
  );
}
