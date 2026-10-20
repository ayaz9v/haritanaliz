/** Thrown when a data file (manifest, config, region index) does not have the expected shape. */
export class DataFormatError extends Error {
  override name = "DataFormatError";
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function expectRecord(value: unknown, where: string): Record<string, unknown> {
  if (!isRecord(value)) throw new DataFormatError(`${where}: expected an object`);
  return value;
}

export function expectArray(value: unknown, where: string): unknown[] {
  if (!Array.isArray(value)) throw new DataFormatError(`${where}: expected an array`);
  return value as unknown[];
}

export function expectString(value: unknown, where: string, pattern?: RegExp): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new DataFormatError(`${where}: expected a non-empty string`);
  }
  if (pattern && !pattern.test(value)) {
    throw new DataFormatError(`${where}: "${value}" does not match ${String(pattern)}`);
  }
  return value;
}

export function expectNumber(value: unknown, where: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new DataFormatError(`${where}: expected a number`);
  }
  return value;
}

export function optionalString(value: unknown, where: string): string | null {
  return value === undefined || value === null ? null : expectString(value, where);
}
