interface ImportMetaEnv {
  /**
   * Base URL of the published data (the folder that holds manifest.json).
   * Defaults to the bundled sample in public/data-sample.
   */
  readonly VITE_DATA_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
