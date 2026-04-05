/**
 * IPC 处理器
 *
 * 处理渲染进程与主进程之间的通信
 */

import { app, BrowserWindow, dialog, ipcMain, shell } from "electron";
import { PythonManager } from "./pythonManager";

export function registerIpcHandlers(
  pythonManager: PythonManager,
  mainWindow: BrowserWindow | null,
): void {
  // 获取 API URL
  ipcMain.handle("get-api-url", () => {
    return pythonManager.getBaseUrl();
  });

  // 打开文件选择对话框
  ipcMain.handle("open-file-dialog", async (event, options) => {
    const result = await dialog.showOpenDialog({
      properties: options?.multiple
        ? ["openFile", "multiSelections"]
        : ["openFile"],
      filters: options?.filters || [
        { name: "Video Files", extensions: ["mp4", "mkv", "avi", "mov", "webm"] },
        { name: "Audio Files", extensions: ["mp3", "wav", "flac", "aac", "m4a"] },
        { name: "All Files", extensions: ["*"] },
      ],
      defaultPath: options?.defaultPath,
    });
    return result.filePaths;
  });

  // 打开保存文件对话框
  ipcMain.handle("save-file-dialog", async (event, options) => {
    const result = await dialog.showSaveDialog({
      filters: options?.filters || [
        { name: "Subtitle Files", extensions: ["srt", "ass", "vtt"] },
      ],
      defaultPath: options?.defaultPath,
    });
    return result.filePath;
  });

  // 打开目录选择对话框
  ipcMain.handle("open-directory-dialog", async (event, options) => {
    const result = await dialog.showOpenDialog({
      properties: ["openDirectory", "createDirectory"],
      defaultPath: options?.defaultPath,
    });
    return result.filePaths[0];
  });

  // 在文件管理器中显示
  ipcMain.handle("open-file-location", async (event, filePath: string) => {
    shell.showItemInFolder(filePath);
  });

  // 获取应用版本
  ipcMain.handle("get-app-version", () => {
    return app.getVersion();
  });

  // 获取应用路径
  ipcMain.handle("get-app-path", () => {
    return app.getAppPath();
  });

  // 获取用户数据路径
  ipcMain.handle("get-user-data-path", () => {
    return app.getPath("userData");
  });

  // 退出应用
  ipcMain.handle("quit-app", async () => {
    app.quit();
  });

  // 重启应用
  ipcMain.handle("restart-app", async () => {
    app.relaunch();
    app.quit();
  });

  // 获取平台信息
  ipcMain.handle("get-platform", () => {
    return {
      platform: process.platform,
      arch: process.arch,
      isMac: process.platform === "darwin",
      isWindows: process.platform === "win32",
    };
  });

  // 窗口控制（Windows 无边框窗口需要）
  ipcMain.handle("window-minimize", () => {
    mainWindow?.minimize();
  });

  ipcMain.handle("window-maximize", () => {
    if (mainWindow?.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow?.maximize();
    }
  });

  ipcMain.handle("window-close", () => {
    mainWindow?.close();
  });

  ipcMain.handle("window-is-maximized", () => {
    return mainWindow?.isMaximized() ?? false;
  });

  console.log("[IPC] Handlers registered");
}
