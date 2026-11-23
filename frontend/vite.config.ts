import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: { port: 5173, proxy: { "/api": "http://localhost:8000" } },
  build: {
    outDir: "dist",
    rollupOptions: {
      output: {
        // Assign UI dependencies first so the chart vendor stays lazy.
        codeSplitting: {
          groups: [
            { name: "vendor-ui", test: /[\\/]node_modules[\\/](react|react-dom|scheduler|clsx|use-sync-external-store)[\\/]/, priority: 20 },
            { name: "vendor-recharts", test: /[\\/]node_modules[\\/]recharts[\\/]/ },
            { name: "vendor-katex", test: /[\\/]node_modules[\\/]katex[\\/]/ },
          ],
        },
      },
    },
  },
  test: { environment: "jsdom", setupFiles: ["./src/test/setup.ts"] },
});
