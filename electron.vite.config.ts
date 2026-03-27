import { resolve } from "path";
import { defineConfig, externalizeDepsPlugin } from "electron-vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()],
    build: {
      outDir: "dist/electron/main",
      rollupOptions: {
        input: {
          index: resolve(__dirname, "src/electron/main/index.ts"),
        },
      },
    },
  },
  preload: {
    plugins: [externalizeDepsPlugin()],
    build: {
      outDir: "dist/electron/preload",
      rollupOptions: {
        input: {
          index: resolve(__dirname, "src/electron/preload/index.ts"),
        },
      },
    },
  },
  renderer: {
    root: resolve(__dirname, "src/electron/renderer"),
    build: {
      outDir: "dist/electron/renderer",
      rollupOptions: {
        input: {
          index: resolve(__dirname, "src/electron/renderer/index.html"),
        },
      },
    },
    plugins: [react()],
  },
});
