import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        // Docker Compose points this at the backend service.
        target: loadEnv(mode, ".", "AEGIS_").AEGIS_API_PROXY_TARGET ?? "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/setupTests.ts",
    // Component tests exercise the real API client; demo-mode tests opt in.
    env: { VITE_DATA_MODE: "live" },
  },
}));
