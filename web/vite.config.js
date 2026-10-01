import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The app always calls /api/*; in production Caddy strips the prefix and
// proxies to the api container, and this dev proxy mirrors that, so the
// bundle needs no base-URL configuration and no CORS anywhere.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_PROXY_TARGET || "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
