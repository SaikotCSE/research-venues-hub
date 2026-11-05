/// <reference types="vitest" />
import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The React app is built into webapp/static/webapp/ (committed, served by WhiteNoise at /static/webapp/).
// Django renders the HTML shell and resolves the entry through .vite/manifest.json (see webapp/vite.py).
export default defineConfig(({ command }) => ({
  base: command === "build" ? "/static/webapp/" : "/",
  plugins: [react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./frontend/src", import.meta.url)) },
  },
  build: {
    outDir: "webapp/static/webapp",
    emptyOutDir: true,
    manifest: true,
    sourcemap: false,
    target: "es2020",
    reportCompressedSize: false,
    chunkSizeWarningLimit: 700,
    rollupOptions: {
      input: "frontend/src/main.tsx",
      output: {
        // A handful of long-lived, shared chunks instead of dozens of tiny ones; pages stay separate.
        manualChunks(id) {
          if (id.includes("node_modules")) {
            if (/[\\/]node_modules[\\/](react|react-dom|scheduler|react-router|react-router-dom|@remix-run)[\\/]/.test(id)) return "react";
            if (/[\\/]@tanstack[\\/]/.test(id)) return "query";
            if (
              /[\\/](@radix-ui|@floating-ui|react-remove-scroll|react-remove-scroll-bar|react-style-singleton|use-callback-ref|use-sidecar|aria-hidden|get-nonce|detect-node-es)[\\/]/.test(
                id,
              )
            )
              return "radix";
            if (/[\\/]lucide-react[\\/]/.test(id)) return "icons";
            return undefined;
          }
          if (/frontend[\\/]src[\\/](lib|hooks|providers|components)[\\/]/.test(id) && !/command-palette/.test(id)) return "app";
          if (/frontend[\\/]src[\\/]pages[\\/](not-found|auth[\\/](auth-layout|password-input|code-step))\.tsx$/.test(id)) return "app";
          return undefined;
        },
      },
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    origin: "http://localhost:5173",
    cors: true,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["frontend/src/test/setup.ts"],
    include: ["frontend/src/**/*.test.{ts,tsx}"],
    css: false,
  },
}));
