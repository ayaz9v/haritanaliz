/// <reference types="vitest/config" />
import path from "node:path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
  build: {
    rolldownOptions: {
      output: {
        // Rarely changing libraries get their own chunks so browsers keep them cached
        // across deploys of the app code.
        codeSplitting: {
          groups: [
            {
              name: "maplibre",
              test: /node_modules[\\/](maplibre-gl|pmtiles|fflate)[\\/]/,
              priority: 20,
            },
            {
              name: "react",
              test: /node_modules[\\/](react|react-dom|scheduler)[\\/]/,
              priority: 10,
            },
            { name: "vendor", test: /node_modules[\\/]/, priority: 0 },
          ],
        },
      },
    },
    // MapLibre alone is about 1.1 MB minified (~300 kB gzip) and cannot be split further.
    chunkSizeWarningLimit: 1100,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
  },
});
