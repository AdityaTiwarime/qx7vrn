/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The API runs separately in development (uvicorn on :8000). /api is proxied to it so the
// browser sees one origin, exactly like production (Vercel rewrites / nginx in Docker).
const proxy = { "/api": process.env.API_URL ?? "http://localhost:8000" };

export default defineConfig({
  plugins: [react()],
  server: { proxy },
  preview: { proxy },
  build: {
    // Recharts (with d3) is ~500 kB minified on its own; it is split into its own cached chunk.
    chunkSizeWarningLimit: 600,
    rollupOptions: { output: { manualChunks: { react: ["react", "react-dom"], charts: ["recharts"] } } },
  },
  test: { environment: "jsdom" },
});
