import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// daemon 同源伺服：构建产物直接输出 webui/（daemon 的 _webui_dir 指向这里）
export default defineConfig({
  root: "src",
  plugins: [react()],
  build: {
    outDir: "../webui",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    // 前端开发模式：vite dev server 代理 API 与 WS 到本机 daemon
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8765",
        changeOrigin: true,
      },
      "/ws": {
        target: "http://127.0.0.1:8765",
        ws: true,
        changeOrigin: true,
      },
    },
  },
});
