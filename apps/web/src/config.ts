/**
 * Base URL of the published data, without a trailing slash. In production this is our own
 * domain in front of Cloudflare R2; r2.dev URLs are for development only.
 */
// `||` (not `??`) so that an empty VITE_DATA_BASE_URL also falls back to the sample.
export const DATA_BASE_URL = (
  import.meta.env.VITE_DATA_BASE_URL || `${import.meta.env.BASE_URL}data-sample`
).replace(/\/+$/, "");
