import { readFileSync } from "node:fs";
import path from "node:path";

// Vitest runs from apps/web (the Vite root). import.meta.url is not a file: URL under jsdom,
// so paths are resolved from the working directory.
const SAMPLE_DIR = path.resolve(process.cwd(), "public", "data-sample");

/** Reads a JSON file from public/data-sample (the bundled sample data release). */
export function readSampleJson(relativePath: string): unknown {
  return JSON.parse(readFileSync(path.join(SAMPLE_DIR, relativePath), "utf-8")) as unknown;
}
