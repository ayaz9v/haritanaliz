import { describe, expect, it } from "vitest";
import { readSampleJson } from "@/test/fixtures";
import { latestVersion, parseManifest } from "./manifest";
import { parseRegionIndex } from "./regions";
import { groupCategories, parseWebConfig, zoomBandAt } from "./webConfig";

function sampleFile(key: string): unknown {
  const version = latestVersion(parseManifest(readSampleJson("manifest.json")));
  const file = version.files[key];
  if (!file) throw new Error(`sample manifest has no "${key}" file`);
  return readSampleJson(`${version.path}${file}`);
}

describe("sample config.json", () => {
  const config = parseWebConfig(sampleFile("config"));

  it("contains the 23 starting categories in 6 groups", () => {
    expect(config.categories).toHaveLength(23);
    expect(config.category_groups).toHaveLength(6);
    expect(config.categories.map((category) => category.name)).toContain("Zincir market");
  });

  it("groups categories in group order", () => {
    const sections = groupCategories(config);
    expect(sections.map((section) => section.group.id)).toEqual(
      config.category_groups.map((group) => group.id),
    );
    expect(sections.flatMap((section) => section.categories)).toHaveLength(23);
  });

  it("maps zoom levels to the three bands", () => {
    const band = (zoom: number) => zoomBandAt(config.zoom_bands, zoom)?.id;
    expect(band(5)).toBe("country");
    expect(band(9)).toBe("district");
    expect(band(13.99)).toBe("district");
    expect(band(14)).toBe("street");
    expect(band(30)).toBe("street");
    expect(band(-1)).toBeUndefined();
  });
});

describe("parseWebConfig", () => {
  it("rejects categories in unknown groups", () => {
    const config = {
      schema_version: 1,
      zoom_bands: [],
      category_groups: [{ id: "health", name: "Sağlık" }],
      categories: [{ id: "cafe", name: "Kafe", group: "food_drink" }],
    };
    expect(() => parseWebConfig(config)).toThrow(/unknown group "food_drink"/);
  });
});

describe("sample regions.json", () => {
  it("lists the 81 provinces with plate-code ids", () => {
    const { regions } = parseRegionIndex(sampleFile("regions"));
    expect(regions).toHaveLength(81);
    expect(new Set(regions.map((region) => region.id)).size).toBe(81);
    expect(regions.every((region) => region.level === "il")).toBe(true);
    expect(regions.find((region) => region.id === "il-34")?.name).toBe("İstanbul");
  });
});
