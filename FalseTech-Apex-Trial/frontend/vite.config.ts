import { defineConfig, loadEnv } from "vite";

const DEFAULT_WORKER_URL = "https://falsetech-apex-tracker-proxy.falsetech-andrew.workers.dev";

function cleanApiTarget(value: string | undefined): string {
  const target = value?.trim().replace(/\/+$/, "");
  return target || DEFAULT_WORKER_URL;
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiTarget = cleanApiTarget(env.VITE_API_BASE_URL || process.env.VITE_API_BASE_URL);

  return {
    server: {
      host: "localhost",
      port: 5173,
      strictPort: true,
      proxy: {
        "/api": {
          target: apiTarget,
          changeOrigin: true,
          secure: true,
        },
      },
    },
    preview: {
      host: "localhost",
      port: 4173,
      strictPort: true,
    },
  };
});
