import type { ExpressionSpecification, Map as MapLibreMap } from "maplibre-gl";

/** Turkish name first, then the Latin-script name, then the local name. */
export const TURKISH_LABEL: ExpressionSpecification = [
  "coalesce",
  ["get", "name:tr"],
  ["get", "name:latin"],
  ["get", "name"],
];

type LabelMap = Pick<MapLibreMap, "getStyle" | "getLayoutProperty" | "setLayoutProperty">;

/**
 * Switches the base map's name labels (places, water, roads) to Turkish. OpenFreeMap styles
 * prefer English names (`name_en`) with a second line in the local script; labels that do not
 * show names, such as road numbers (`ref`), are left alone.
 */
export function applyTurkishLabels(map: LabelMap): void {
  for (const layer of map.getStyle().layers) {
    if (layer.type !== "symbol") continue;
    const textField: unknown = map.getLayoutProperty(layer.id, "text-field");
    if (textField !== undefined && JSON.stringify(textField).includes('"name')) {
      map.setLayoutProperty(layer.id, "text-field", TURKISH_LABEL);
    }
  }
}
