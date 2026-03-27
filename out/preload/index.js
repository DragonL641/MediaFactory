"use strict";
const electron = require("electron");
const electronAPI = {
  // API 相关
  getApiUrl: () => electron.ipcRenderer.invoke("get-api-url"),
  // 文件对话框
  openFileDialog: (options) => electron.ipcRenderer.invoke("open-file-dialog", options),
  saveFileDialog: (options) => electron.ipcRenderer.invoke("save-file-dialog", options),
  openDirectoryDialog: (options) => electron.ipcRenderer.invoke("open-directory-dialog", options),
  // 文件操作
  openFileLocation: (filePath) => electron.ipcRenderer.invoke("open-file-location", filePath),
  // 应用信息
  getAppVersion: () => electron.ipcRenderer.invoke("get-app-version"),
  getAppPath: () => electron.ipcRenderer.invoke("get-app-path"),
  getUserDataPath: () => electron.ipcRenderer.invoke("get-user-data-path"),
  getPlatform: () => electron.ipcRenderer.invoke("get-platform"),
  // 应用控制
  quitApp: () => electron.ipcRenderer.invoke("quit-app"),
  restartApp: () => electron.ipcRenderer.invoke("restart-app"),
  // 事件监听
  onUpdateAvailable: (callback) => {
    electron.ipcRenderer.on("update-available", (_event, version) => callback(version));
  },
  onPythonError: (callback) => {
    electron.ipcRenderer.on("python-error", (_event, error) => callback(error));
  }
};
electron.contextBridge.exposeInMainWorld("electronAPI", electronAPI);
