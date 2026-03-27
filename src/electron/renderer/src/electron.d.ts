/**
 * Electron API 类型声明
 *
 * 声明 window.electronAPI 供渲染进程使用
 */

interface FileFilter {
  name: string;
  extensions: string[];
}

interface OpenFileDialogOptions {
  multiple?: boolean;
  filters?: FileFilter[];
  defaultPath?: string;
}

interface SaveFileDialogOptions {
  filters?: FileFilter[];
  defaultPath?: string;
}

interface DirectoryDialogOptions {
  defaultPath?: string;
}

interface PlatformInfo {
  platform: string;
  arch: string;
  isMac: boolean;
  isWindows: boolean;
  isLinux: boolean;
}

interface ElectronAPI {
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

interface Window {
  electronAPI: ElectronAPI;
}
