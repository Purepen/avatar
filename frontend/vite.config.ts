import { resolve } from "node:path";
import { defineConfig } from "vite";

// Multi-page build: / (visitor chat) and /admin (dashboard).
// The dev server proxies API calls to the FastAPI backend on :8000;
// the exact-prefix regex keeps /admin.html itself served by Vite.
export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        admin: resolve(__dirname, "admin.html"),
      },
    },
  },
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "^/admin/(login|logout|session|conversations)": {
        target: "http://localhost:8000",
      },
    },
  },
});
