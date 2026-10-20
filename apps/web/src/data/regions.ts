import { DataFormatError, expectArray, expectRecord, expectString } from "@/lib/validate";

export const REGION_LEVELS = ["il", "ilce", "mahalle", "koy"] as const;
export type RegionLevel = (typeof REGION_LEVELS)[number];

export const REGION_LEVEL_LABELS: Record<RegionLevel, string> = {
  il: "İl",
  ilce: "İlçe",
  mahalle: "Mahalle",
  koy: "Köy",
};

/** Region ids look like "il-06"; the pipeline defines the district and neighbourhood codes. */
export const REGION_ID_PATTERN = /^[a-z]+-[0-9a-z_-]+$/;

export interface Region {
  id: string;
  name: string;
  level: RegionLevel;
  /** Id of the enclosing region (null for provinces). */
  parent: string | null;
}

/** regions.json of a data version: the searchable list of administrative units. */
export interface RegionIndex {
  schema_version: 1;
  regions: Region[];
}

export function parseRegionIndex(input: unknown): RegionIndex {
  const root = expectRecord(input, "regions");
  if (root.schema_version !== 1) {
    throw new DataFormatError(`regions: unsupported schema_version ${String(root.schema_version)}`);
  }
  const regions = expectArray(root.regions, "regions.regions").map((item, index) => {
    const where = `regions.regions[${index}]`;
    const region = expectRecord(item, where);
    const level = expectString(region.level, `${where}.level`);
    if (!isRegionLevel(level)) {
      throw new DataFormatError(`${where}.level: unknown level "${level}"`);
    }
    return {
      id: expectString(region.id, `${where}.id`, REGION_ID_PATTERN),
      name: expectString(region.name, `${where}.name`),
      level,
      parent:
        region.parent === undefined || region.parent === null
          ? null
          : expectString(region.parent, `${where}.parent`, REGION_ID_PATTERN),
    };
  });
  return { schema_version: 1, regions };
}

function isRegionLevel(value: string): value is RegionLevel {
  return (REGION_LEVELS as readonly string[]).includes(value);
}
