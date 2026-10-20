import { addProtocol, setWorkerUrl } from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { Protocol } from "pmtiles";

/**
 * Shared PMTiles protocol. Map sources can use "pmtiles://https://<host>/<file>.pmtiles";
 * MapLibre then reads only the byte ranges it needs from the archive (HTTP range requests
 * against R2), so no tile server is involved.
 */
export const pmtilesProtocol = new Protocol({ metadata: true });

let initialized = false;

/** One-time MapLibre setup: the worker URL (required with bundlers since v6) and pmtiles://. */
export function setupMapLibre(): void {
  if (initialized) return;
  setWorkerUrl(workerUrl);
  addProtocol("pmtiles", pmtilesProtocol.tile);
  initialized = true;
}
