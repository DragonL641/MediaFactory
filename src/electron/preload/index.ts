/**
 * 预加载脚本
 *
 * 通过 contextBridge 安全地暴露 API 给渲染进程
 */

import { contextBridge, ipcRenderer } from "electron";

// API 接口定义
export interface ElectronAPI {
  // API 相关
  getApiUrl: () => Promise<string>;

  // 文件对话框
  openFileDialog: (options?: OpenFileDialogOptions) => Promise<string[]>;
  saveFileDialog: (options?: SaveFileDialogOptions) => Promise<string>;
  openDirectoryDialog: (options?: DirectoryDialogOptions) => Promise<string>;

  // 文件操作
  openFileLocation: (filePath: string) => Promise<void>;

  // 应用信息
  getAppVersion: () => Promise<string>;
  getAppPath: () => Promise<string>;
  getUserDataPath: () => Promise<string>;
  getPlatform: () => Promise<PlatformInfo>;

  // 应用控制
  quitApp: () => Promise<void>;
  restartApp: () => Promise<void>;

  // 事件监听
  onUpdateAvailable: (callback: (version: string) => void) => void;
  onPythonError: (callback: (error: string) => void) => void;
}

export interface OpenFileDialogOptions {
  multiple?: boolean;
  filters?: FileFilter[];
  defaultPath?: string;
}

export interface SaveFileDialogOptions {
  filters?: FileFilter[];
  defaultPath?: string;
}

export interface DirectoryDialogOptions {
  defaultPath?: string;
}

export interface FileFilter {
  name: string;
  extensions: string[];
}

export interface PlatformInfo {
  platform: string;
  arch: string;
  isMac: boolean;
  isWindows: boolean;
  isLinux: boolean;
}

// 暴露 API 给渲染进程
const electronAPI: ElectronAPI = {
  // API 相关
  getApiUrl: () => ipcRenderer.invoke("get-api-url"),

  // 文件对话框
  openFileDialog: (options) => ipcRenderer.invoke("open-file-dialog", options),
  saveFileDialog: (options) => ipcRenderer.invoke("save-file-dialog", options),
  openDirectoryDialog: (options) =>
    ipcRenderer.invoke("open-directory-dialog", options),

  // 文件操作
  openFileLocation: (filePath) => ipcRenderer.invoke("open-file-location", filePath),

  // 应用信息
  getAppVersion: () => ipcRenderer.invoke("get-app-version"),
  getAppPath: () => ipcRenderer.invoke("get-app-path"),
  getUserDataPath: () => ipcRenderer.invoke("get-user-data-path"),
  getPlatform: () => ipcRenderer.invoke("get-platform"),

  // 应用控制
  quitApp: () => ipcRenderer.invoke("quit-app"),
  restartApp: () => ipcRenderer.invoke("restart-app"),

  // 事件监听
  onUpdateAvailable: (callback) => {
    ipcRenderer.on("update-available", (_event, version) => callback(version));
  },
  onPythonError: (callback) => {
    ipcRenderer.on("python-error", (_event, error) => callback(error));
  },
};

// 通过 contextBridge 安全暴露
contextBridge.exposeInMainWorld("electronAPI", electronAPI);

// 类型声明（导出给 TypeScript 使用）
export type { ElectronAPI };
