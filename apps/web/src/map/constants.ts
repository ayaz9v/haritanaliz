import type { LngLatBoundsLike } from "maplibre-gl";

/** OpenFreeMap "positron": a light, low-contrast base map that keeps choropleths readable. */
export const BASEMAP_STYLE_URL = "https://tiles.openfreemap.org/styles/positron";

/** Initial view: the whole of Türkiye, as [west, south, east, north]. */
export const TURKEY_BOUNDS: LngLatBoundsLike = [25.6, 35.8, 44.85, 42.15];

/** Padding in pixels around TURKEY_BOUNDS when fitting the view. */
export const FIT_PADDING = 24;

/** Turkish labels for MapLibre's built-in controls. */
export const MAP_LOCALE_TR: Record<string, string> = {
  "AttributionControl.ToggleAttribution": "Atıfları göster veya gizle",
  "AttributionControl.MapFeedback": "Harita geri bildirimi",
  "FullscreenControl.Enter": "Tam ekran",
  "FullscreenControl.Exit": "Tam ekrandan çık",
  "GeolocateControl.FindMyLocation": "Konumumu bul",
  "GeolocateControl.LocationNotAvailable": "Konum kullanılamıyor",
  "LogoControl.Title": "MapLibre logosu",
  "Map.Title": "Harita",
  "NavigationControl.ResetBearing": "Kuzeye döndür",
  "NavigationControl.ZoomIn": "Yakınlaştır",
  "NavigationControl.ZoomOut": "Uzaklaştır",
  "Popup.Close": "Kapat",
  "ScaleControl.Meters": "m",
  "ScaleControl.Kilometers": "km",
};
