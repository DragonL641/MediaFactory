/**
 * Electron 主进程入口
 *
 * 负责应用生命周期、窗口管理、Python 后端进程管理
 */

import { app, BrowserWindow, dialog, ipcMain } from "electron";
import * as path from "path";
import { PythonManager } from "./pythonManager";
import { registerIpcHandlers } from "./ipcHandlers";

let mainWindow: BrowserWindow | null = null;
let pythonManager: PythonManager | null = null;
let ipcHandlersRegistered = false;

// 判断是否为开发模式
const isDev = !app.isPackaged;

async function createWindow(): Promise<void> {
  // 创建主窗口
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    title: "MediaFactory",
    show: false, // 等待 Python 就绪后再显示
    webPreferences: {
      preload: path.join(__dirname, "../preload/index.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
    // macOS 特定样式
    titleBarStyle: process.platform === "darwin" ? "hiddenInset" : "default",
    frame: process.platform === "darwin" ? true : false,
    trafficLightPosition: { x: 15, y: 10 },
  });

  // 注册 IPC 处理器（只注册一次）
  if (!ipcHandlersRegistered && pythonManager) {
    registerIpcHandlers(pythonManager);
    ipcHandlersRegistered = true;
  }

  // 加载页面
  if (isDev) {
    // 开发模式：加载 Vite dev server
    const devServerUrl = "http://localhost:5173";
    await mainWindow.loadURL(devServerUrl);
    mainWindow.webContents.openDevTools();
  } else {
    // 生产模式：加载打包后的文件
    await mainWindow.loadFile(
      path.join(__dirname, "../renderer/index.html")
    );
  }

  // 窗口关闭处理
  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

async function startApp(): Promise<void> {
  try {
    // 启动 Python 后端
    pythonManager = new PythonManager();
    await pythonManager.start();

    // 创建窗口
    await createWindow();

    // 显示窗口
    if (mainWindow) {
      mainWindow.show();
    }
  } catch (error) {
    console.error("Failed to start application:", error);
    dialog.showErrorBox(
      "启动失败",
      `无法启动 MediaFactory 后端服务：\n${error}\n\n请检查 Python 环境配置。`
    );
    app.quit(1);
  }
}

// 应用就绪
app.whenReady().then(startApp);

// 所有窗口关闭时退出（macOS 除外）
app.on("window-all-closed", async () => {
  // 停止 Python 后端
  if (pythonManager) {
    await pythonManager.stop();
  }

  if (process.platform !== "darwin") {
    app.quit();
  }
});

// 应用退出前清理
app.on("before-quit", async (event) => {
  if (pythonManager) {
    event.preventDefault();
    await pythonManager.stop();
    app.exit(0);
  }
});

// macOS 激活应用
app.on("activate", () => {
  if (mainWindow === null) {
    createWindow();
  }
});
