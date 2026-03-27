"use strict";
const electron = require("electron");
const path = require("path");
const child_process = require("child_process");
const http = require("http");
function _interopNamespaceDefault(e) {
  const n = Object.create(null, { [Symbol.toStringTag]: { value: "Module" } });
  if (e) {
    for (const k in e) {
      if (k !== "default") {
        const d = Object.getOwnPropertyDescriptor(e, k);
        Object.defineProperty(n, k, d.get ? d : {
          enumerable: true,
          get: () => e[k]
        });
      }
    }
  }
  n.default = e;
  return Object.freeze(n);
}
const path__namespace = /* @__PURE__ */ _interopNamespaceDefault(path);
const http__namespace = /* @__PURE__ */ _interopNamespaceDefault(http);
class PythonManager {
  process = null;
  port = 8765;
  baseUrl = "";
  isReady = false;
  maxRetries = 3;
  healthCheckTimeout = 3e4;
  // 30 seconds
  /**
   * 启动 Python 后端
   */
  async start() {
    const pythonExe = this.getPythonExecutable();
    const port = await this.findAvailablePort();
    console.log(`[PythonManager] Starting Python backend on port ${port}...`);
    console.log(`[PythonManager] Python executable: ${pythonExe}`);
    this.port = port;
    this.baseUrl = `http://127.0.0.1:${port}`;
    const args = [
      "-m",
      "uvicorn",
      "mediafactory.api.main:app",
      "--host",
      "127.0.0.1",
      "--port",
      port.toString()
    ];
    if (!electron.app.isPackaged) {
      args.push("--reload");
    }
    return new Promise((resolve, reject) => {
      try {
        this.process = child_process.spawn(pythonExe, args, {
          cwd: this.getAppRoot(),
          env: {
            ...process.env,
            PYTHONUNBUFFERED: "1",
            PYTHONIOENCODING: "utf-8"
          }
        });
        this.process.stdout?.on("data", (data) => {
          const output = data.toString();
          console.log(`[Python] ${output.trim()}`);
          if (output.includes("Uvicorn running")) {
            this.isReady = true;
          }
        });
        this.process.stderr?.on("data", (data) => {
          const output = data.toString();
          console.error(`[Python Error] ${output.trim()}`);
        });
        this.process.on("error", (error) => {
          console.error("[PythonManager] Process error:", error);
          reject(error);
        });
        this.process.on("exit", (code, signal) => {
          console.log(`[PythonManager] Process exited with code ${code}, signal ${signal}`);
          this.process = null;
          this.isReady = false;
        });
        this.waitForReady().then(() => {
          console.log("[PythonManager] Python backend is ready");
          resolve();
        }).catch((error) => {
          reject(error);
        });
      } catch (error) {
        reject(error);
      }
    });
  }
  /**
   * 停止 Python 后端
   */
  async stop() {
    if (!this.process) {
      return;
    }
    console.log("[PythonManager] Stopping Python backend...");
    return new Promise((resolve) => {
      const timeout = setTimeout(() => {
        if (this.process) {
          console.log("[PythonManager] Force killing Python process");
          this.process.kill("SIGKILL");
        }
        resolve();
      }, 5e3);
      this.process.on("exit", () => {
        clearTimeout(timeout);
        this.process = null;
        this.isReady = false;
        resolve();
      });
      this.process.kill("SIGTERM");
    });
  }
  /**
   * 获取 API 基础 URL
   */
  getBaseUrl() {
    return this.baseUrl;
  }
  /**
   * 检查后端是否就绪
   */
  isBackendReady() {
    return this.isReady;
  }
  /**
   * 获取 Python 可执行文件路径
   */
  getPythonExecutable() {
    if (electron.app.isPackaged) {
      const appPath = electron.app.getAppPath();
      if (process.platform === "darwin") {
        return path__namespace.join(appPath, "Contents/MacOS/python/bin/python");
      } else if (process.platform === "win32") {
        return path__namespace.join(appPath, "python/python.exe");
      }
    }
    const venvPython = path__namespace.join(process.cwd(), ".venv/bin/python");
    const fs = require("fs");
    if (fs.existsSync(venvPython)) {
      return venvPython;
    }
    return process.platform === "win32" ? "python" : "python3";
  }
  /**
   * 获取应用根目录
   */
  getAppRoot() {
    if (electron.app.isPackaged) {
      return path__namespace.dirname(electron.app.getAppPath());
    }
    return process.cwd();
  }
  /**
   * 查找可用端口
   */
  async findAvailablePort() {
    const startPort = this.port;
    const maxPort = startPort + 10;
    for (let port = startPort; port < maxPort; port++) {
      if (await this.isPortAvailable(port)) {
        return port;
      }
    }
    throw new Error(`No available port found between ${startPort} and ${maxPort - 1}`);
  }
  /**
   * 检查端口是否可用
   */
  isPortAvailable(port) {
    return new Promise((resolve) => {
      const server = http__namespace.createServer();
      server.once("error", () => resolve(false));
      server.once("listening", () => {
        server.close();
        resolve(true);
      });
      server.listen(port, "127.0.0.1");
    });
  }
  /**
   * 等待后端就绪
   */
  async waitForReady() {
    const startTime = Date.now();
    while (Date.now() - startTime < this.healthCheckTimeout) {
      try {
        const isHealthy = await this.checkHealth();
        if (isHealthy) {
          return;
        }
      } catch {
      }
      await new Promise((resolve) => setTimeout(resolve, 1e3));
    }
    throw new Error("Python backend failed to start within timeout");
  }
  /**
   * 检查后端健康状态
   */
  checkHealth() {
    return new Promise((resolve) => {
      const req = http__namespace.request(
        {
          hostname: "127.0.0.1",
          port: this.port,
          path: "/health",
          method: "GET",
          timeout: 2e3
        },
        (res) => {
          resolve(res.statusCode === 200);
        }
      );
      req.on("error", () => resolve(false));
      req.on("timeout", () => {
        req.destroy();
        resolve(false);
      });
      req.end();
    });
  }
}
function registerIpcHandlers(pythonManager2) {
  electron.ipcMain.handle("get-api-url", () => {
    return pythonManager2.getBaseUrl();
  });
  electron.ipcMain.handle("open-file-dialog", async (event, options) => {
    const result = await electron.dialog.showOpenDialog({
      properties: options?.multiple ? ["openFile", "multiSelections"] : ["openFile"],
      filters: options?.filters || [
        { name: "Video Files", extensions: ["mp4", "mkv", "avi", "mov", "webm"] },
        { name: "Audio Files", extensions: ["mp3", "wav", "flac", "aac", "m4a"] },
        { name: "All Files", extensions: ["*"] }
      ],
      defaultPath: options?.defaultPath
    });
    return result.filePaths;
  });
  electron.ipcMain.handle("save-file-dialog", async (event, options) => {
    const result = await electron.dialog.showSaveDialog({
      filters: options?.filters || [
        { name: "Subtitle Files", extensions: ["srt", "ass", "vtt"] }
      ],
      defaultPath: options?.defaultPath
    });
    return result.filePath;
  });
  electron.ipcMain.handle("open-directory-dialog", async (event, options) => {
    const result = await electron.dialog.showOpenDialog({
      properties: ["openDirectory", "createDirectory"],
      defaultPath: options?.defaultPath
    });
    return result.filePaths[0];
  });
  electron.ipcMain.handle("open-file-location", async (event, filePath) => {
    electron.shell.showItemInFolder(filePath);
  });
  electron.ipcMain.handle("get-app-version", () => {
    return electron.app.getVersion();
  });
  electron.ipcMain.handle("get-app-path", () => {
    return electron.app.getAppPath();
  });
  electron.ipcMain.handle("get-user-data-path", () => {
    return electron.app.getPath("userData");
  });
  electron.ipcMain.handle("quit-app", async () => {
    electron.app.quit();
  });
  electron.ipcMain.handle("restart-app", async () => {
    electron.app.relaunch();
    electron.app.quit();
  });
  electron.ipcMain.handle("get-platform", () => {
    return {
      platform: process.platform,
      arch: process.arch,
      isMac: process.platform === "darwin",
      isWindows: process.platform === "win32",
      isLinux: process.platform === "linux"
    };
  });
  console.log("[IPC] Handlers registered");
}
let mainWindow = null;
let pythonManager = null;
const isDev = !electron.app.isPackaged;
async function createWindow() {
  mainWindow = new electron.BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    title: "MediaFactory",
    show: false,
    // 等待 Python 就绪后再显示
    webPreferences: {
      preload: path__namespace.join(__dirname, "../preload/index.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    },
    // macOS 特定样式
    titleBarStyle: process.platform === "darwin" ? "hiddenInset" : "default",
    frame: process.platform === "darwin" ? true : false,
    trafficLightPosition: { x: 15, y: 10 }
  });
  registerIpcHandlers(pythonManager);
  if (isDev) {
    const devServerUrl = "http://localhost:5173";
    await mainWindow.loadURL(devServerUrl);
    mainWindow.webContents.openDevTools();
  } else {
    await mainWindow.loadFile(
      path__namespace.join(__dirname, "../renderer/index.html")
    );
  }
  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}
async function startApp() {
  try {
    pythonManager = new PythonManager();
    await pythonManager.start();
    await createWindow();
    if (mainWindow) {
      mainWindow.show();
    }
  } catch (error) {
    console.error("Failed to start application:", error);
    electron.dialog.showErrorBox(
      "启动失败",
      `无法启动 MediaFactory 后端服务：
${error}

请检查 Python 环境配置。`
    );
    electron.app.quit(1);
  }
}
electron.app.whenReady().then(startApp);
electron.app.on("window-all-closed", async () => {
  if (pythonManager) {
    await pythonManager.stop();
  }
  if (process.platform !== "darwin") {
    electron.app.quit();
  }
});
electron.app.on("before-quit", async (event) => {
  if (pythonManager) {
    event.preventDefault();
    await pythonManager.stop();
    electron.app.exit(0);
  }
});
electron.app.on("activate", () => {
  if (mainWindow === null) {
    createWindow();
  }
});
