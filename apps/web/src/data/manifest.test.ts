import { describe, expect, it } from "vitest";
import { readSampleJson } from "@/test/fixtures";
import { DataFormatError } from "@/lib/validate";
import { formatVersionDate, latestVersion, parseManifest, versionFileUrl } from "./manifest";

function release(overrides: Record<string, unknown> = {}) {
  return {
    schema_version: 1,
    latest: "2026-10-01",
    versions: [
      {
        version: "2026-10-01",
        path: "v/2026-10-01/",
        published_at: "2026-10-02T03:00:00Z",
        files: { config: "config.json" },
      },
    ],
    ...overrides,
  };
}

describe("parseManifest", () => {
  it("accepts the bundled sample manifest", () => {
    const manifest = parseManifest(readSampleJson("manifest.json"));
    expect(manifest.sample).toBe(true);
    const latest = latestVersion(manifest);
    expect(latest.path).toBe(`v/${manifest.latest}/`);
    expect(versionFileUrl("https://veri.example.org", latest, "config")).toBe(
      `https://veri.example.org/v/${manifest.latest}/config.json`,
    );
  });

  it("treats a missing sample flag as a real release", () => {
    const manifest = parseManifest(release());
    expect(manifest.sample).toBe(false);
    expect(latestVersion(manifest).sources).toEqual([]);
  });

  it("rejects a latest version that is not listed", () => {
    expect(() => parseManifest(release({ latest: "2026-11-01" }))).toThrow(DataFormatError);
  });

  it("rejects impossible dates", () => {
    expect(() => parseManifest(release({ latest: "2026-02-30" }))).toThrow(/not a valid date/);
  });

  it("rejects a path that belongs to another version", () => {
    const manifest = release();
    manifest.versions[0]!.path = "v/2026-09-01/";
    expect(() => parseManifest(manifest)).toThrow(/does not match version/);
  });

  it("rejects unknown schema versions", () => {
    expect(() => parseManifest(release({ schema_version: 2 }))).toThrow(/schema_version/);
  });

  it("refuses to build URLs for files the version does not have", () => {
    const version = latestVersion(parseManifest(release()));
    expect(() => versionFileUrl("/data", version, "regions")).toThrow(/no "regions" file/);
  });
});

describe("formatVersionDate", () => {
  it("formats dates in Turkish", () => {
    expect(formatVersionDate("2026-10-20")).toBe("20 Ekim 2026");
    expect(formatVersionDate("2026-10-20", "short")).toBe("20 Eki 2026");
    expect(formatVersionDate("2026-01-01")).toBe("1 Ocak 2026");
  });
});
