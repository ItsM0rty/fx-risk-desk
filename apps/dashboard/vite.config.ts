import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const proxy = { "/api": "http://127.0.0.1:8000" };

export default defineConfig({
  plugins: [react()],
  build: { rollupOptions: { output: { manualChunks: { charts: ["recharts"] } } } },
  server: { proxy, port: 5173, strictPort: true },
  preview: { proxy, port: 4173, strictPort: true },
});
