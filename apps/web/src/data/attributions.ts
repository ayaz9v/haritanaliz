export interface Attribution {
  id: string;
  label: string;
  href: string;
}

// Shown in the always-visible attribution bar. Keep in sync with docs/data_sources.md.

/** Base map: OpenFreeMap vector tiles (OpenMapTiles schema, built from OpenStreetMap). */
export const BASEMAP_ATTRIBUTIONS: readonly Attribution[] = [
  { id: "openfreemap", label: "OpenFreeMap", href: "https://openfreemap.org" },
  { id: "openmaptiles", label: "© OpenMapTiles", href: "https://www.openmaptiles.org/" },
];

/** Sources of the analysis data. */
export const DATA_ATTRIBUTIONS: readonly Attribution[] = [
  {
    id: "osm",
    label: "© OpenStreetMap katkıcıları",
    href: "https://www.openstreetmap.org/copyright",
  },
  { id: "overture", label: "Overture Maps Foundation", href: "https://overturemaps.org" },
  { id: "tuik", label: "TÜİK", href: "https://www.tuik.gov.tr" },
  // SEGE: socio-economic development ranking, Ministry of Industry and Technology.
  { id: "sege", label: "SEGE", href: "https://www.sanayi.gov.tr" },
];
