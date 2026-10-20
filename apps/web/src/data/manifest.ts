import {
  DataFormatError,
  expectArray,
  expectRecord,
  expectString,
  optionalString,
} from "@/lib/validate";

/**
 * manifest.json: lists the live data versions and names the one to use (`latest`).
 * Mirrors pipeline/src/haritanaliz/manifest.py; both sides validate the same rules.
 */
export interface Manifest {
  schema_version: 1;
  /** True for the bundled sample data, which is not a real data release. */
  sample: boolean;
  latest: string;
  versions: ManifestVersion[];
}

export interface ManifestVersion {
  /** Release date, YYYY-MM-DD. */
  version: string;
  /** Folder of the version relative to the data base URL, e.g. "v/2026-10-20/". */
  path: string;
  published_at: string;
  /** Files of the version by key, e.g. { config: "config.json" }. */
  files: Record<string, string>;
  sources: ManifestSource[];
}

export interface ManifestSource {
  id: string;
  name: string;
  version: string | null;
  license: string | null;
}

const VERSION_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const PATH_PATTERN = /^[a-z0-9_-]+\/\d{4}-\d{2}-\d{2}\/$/;
const FILE_PATTERN = /^[A-Za-z0-9_-]+(\/[A-Za-z0-9_-]+)*\.[a-z0-9]+$/;

export function parseManifest(input: unknown): Manifest {
  const root = expectRecord(input, "manifest");
  if (root.schema_version !== 1) {
    throw new DataFormatError(
      `manifest: unsupported schema_version ${String(root.schema_version)}`,
    );
  }
  const latest = parseVersionId(root.latest, "manifest.latest");
  const versions = expectArray(root.versions, "manifest.versions").map((item, index) =>
    parseVersion(item, `manifest.versions[${index}]`),
  );
  if (!versions.some((version) => version.version === latest)) {
    throw new DataFormatError(`manifest: latest version ${latest} is not listed in versions`);
  }
  return { schema_version: 1, sample: root.sample === true, latest, versions };
}

export function latestVersion(manifest: Manifest): ManifestVersion {
  const version = manifest.versions.find((item) => item.version === manifest.latest);
  if (!version) {
    throw new DataFormatError(`manifest: latest version ${manifest.latest} is not listed`);
  }
  return version;
}

/** URL of a file in a version, e.g. versionFileUrl(base, version, "config"). */
export function versionFileUrl(baseUrl: string, version: ManifestVersion, key: string): string {
  const file = version.files[key];
  if (file === undefined) {
    throw new DataFormatError(`version ${version.version} has no "${key}" file`);
  }
  return `${baseUrl}/${version.path}${file}`;
}

const longDate = new Intl.DateTimeFormat("tr-TR", {
  day: "numeric",
  month: "long",
  year: "numeric",
  timeZone: "UTC",
});
const shortDate = new Intl.DateTimeFormat("tr-TR", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

/** Formats a version date in Turkish: "20 Ekim 2026", or "20 Eki 2026" when short. */
export function formatVersionDate(version: string, style: "long" | "short" = "long"): string {
  return (style === "short" ? shortDate : longDate).format(new Date(`${version}T00:00:00Z`));
}

function parseVersion(input: unknown, where: string): ManifestVersion {
  const item = expectRecord(input, where);
  const version = parseVersionId(item.version, `${where}.version`);
  const path = expectString(item.path, `${where}.path`, PATH_PATTERN);
  if (!path.endsWith(`/${version}/`)) {
    throw new DataFormatError(`${where}.path: "${path}" does not match version ${version}`);
  }
  const publishedAt = expectString(item.published_at, `${where}.published_at`);
  if (Number.isNaN(Date.parse(publishedAt))) {
    throw new DataFormatError(`${where}.published_at: "${publishedAt}" is not a timestamp`);
  }
  const files: Record<string, string> = {};
  for (const [key, value] of Object.entries(expectRecord(item.files, `${where}.files`))) {
    files[key] = expectString(value, `${where}.files.${key}`, FILE_PATTERN);
  }
  const sources =
    item.sources === undefined
      ? []
      : expectArray(item.sources, `${where}.sources`).map((source, index) =>
          parseSource(source, `${where}.sources[${index}]`),
        );
  return { version, path, published_at: publishedAt, files, sources };
}

function parseSource(input: unknown, where: string): ManifestSource {
  const item = expectRecord(input, where);
  return {
    id: expectString(item.id, `${where}.id`),
    name: expectString(item.name, `${where}.name`),
    version: optionalString(item.version, `${where}.version`),
    license: optionalString(item.license, `${where}.license`),
  };
}

function parseVersionId(value: unknown, where: string): string {
  const version = expectString(value, where, VERSION_PATTERN);
  const date = new Date(`${version}T00:00:00Z`);
  // Rejects impossible dates such as 2026-02-30, which Date silently rolls over.
  if (Number.isNaN(date.getTime()) || !date.toISOString().startsWith(version)) {
    throw new DataFormatError(`${where}: ${version} is not a valid date`);
  }
  return version;
}
