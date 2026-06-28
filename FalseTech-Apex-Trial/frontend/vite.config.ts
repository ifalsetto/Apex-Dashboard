import { defineConfig } from "vite";

const LOCAL_BACKEND_URL = "http://127.0.0.1:8787";

export default defineConfig({
  server: {
    host: "localhost",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: LOCAL_BACKEND_URL,
        changeOrigin: true,
        secure: false,
      },
    },
  },
  preview: {
    host: "localhost",
    port: 4173,
    strictPort: true,
  },
});
