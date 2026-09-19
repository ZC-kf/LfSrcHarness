import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 8620,
    proxy: { "/api": "http://127.0.0.1:8619" }
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test-setup.ts"
  }
});
