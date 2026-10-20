import { skipToken, useQuery } from "@tanstack/react-query";
import { DATA_BASE_URL } from "@/config";
import { latestVersion, parseManifest, versionFileUrl } from "./manifest";
import { parseRegionIndex } from "./regions";
import { parseWebConfig } from "./webConfig";

export async function fetchJson(url: string, signal?: AbortSignal): Promise<unknown> {
  const response = await fetch(url, { signal });
  if (!response.ok) throw new Error(`GET ${url} failed with HTTP ${response.status}`);
  return (await response.json()) as unknown;
}

/** manifest.json changes when a new data version is published, so it is re-checked. */
export function useManifest() {
  return useQuery({
    queryKey: ["manifest", DATA_BASE_URL],
    queryFn: async ({ signal }) =>
      parseManifest(await fetchJson(`${DATA_BASE_URL}/manifest.json`, signal)),
    staleTime: 5 * 60 * 1000,
  });
}

function useLatestVersionFile<T>(key: string, parse: (input: unknown) => T) {
  const { data: manifest } = useManifest();
  const version = manifest ? latestVersion(manifest) : undefined;
  return useQuery({
    queryKey: ["data-file", DATA_BASE_URL, version?.version, key],
    queryFn: version
      ? async ({ signal }) =>
          parse(await fetchJson(versionFileUrl(DATA_BASE_URL, version, key), signal))
      : skipToken,
    // Files inside a version folder never change.
    staleTime: Infinity,
  });
}

export function useWebConfig() {
  return useLatestVersionFile("config", parseWebConfig);
}

export function useRegionIndex() {
  return useLatestVersionFile("regions", parseRegionIndex);
}
