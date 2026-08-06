import react from "@vitejs/plugin-react";
import path from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: true,
  },
  server: {
    port: 5173,
    // Bind mount de Windows/macOS -> contenedor Linux: los eventos inotify
    // nativos no siempre llegan al watcher dentro del contenedor. Sin esto,
    // Vite no recarga cuando el archivo se edita desde el host.
    watch: { usePolling: true, interval: 300 },
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000",
        changeOrigin: true,
      },
      "/ws": {
        target: process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000",
        ws: true,
        changeOrigin: true,
      },
    },
  },
});
