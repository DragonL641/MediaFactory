/**
 * Python 进程管理器
 *
 * 负责 Python 后端进程的生命周期管理
 */

import { app } from "electron";
import { ChildProcess, spawn } from "child_process";
import * as path from "path";
import * as http from "http";

export class PythonManager {
  private process: ChildProcess | null = null;
  private port: number = 8765;
  private baseUrl: string = "";
  private isReady: boolean = false;
  private maxRetries: number = 3;
  private healthCheckTimeout: number = 30000; // 30 seconds

  /**
   * 启动 Python 后端
   */
  async start(): Promise<void> {
    const pythonExe = this.getPythonExecutable();
    const port = await this.findAvailablePort();

    console.log(`[PythonManager] Starting Python backend on port ${port}...`);
    console.log(`[PythonManager] Python executable: ${pythonExe}`);

    this.port = port;
    this.baseUrl = `http://127.0.0.1:${port}`;

    const args = [
      "-m",
      "uvicorn",
      "mediafactory.api.main:get_app",
      "--factory",
      "--host",
      "127.0.0.1",
      "--port",
      port.toString(),
    ];

    // 开发模式添加 reload
    if (!app.isPackaged) {
      args.push("--reload");
    }

    return new Promise((resolve, reject) => {
      try {
        this.process = spawn(pythonExe, args, {
          cwd: this.getAppRoot(),
          env: {
            ...process.env,
            PYTHONUNBUFFERED: "1",
            PYTHONIOENCODING: "utf-8",
          },
        });

        // 监听 stdout
        this.process.stdout?.on("data", (data: Buffer) => {
          const output = data.toString();
          console.log(`[Python] ${output.trim()}`);

          if (output.includes("Uvicorn running")) {
            this.isReady = true;
          }
        });

        // 监听 stderr
        this.process.stderr?.on("data", (data: Buffer) => {
          const output = data.toString();
          console.error(`[Python Error] ${output.trim()}`);
        });

        // 监听进程错误
        this.process.on("error", (error) => {
          console.error("[PythonManager] Process error:", error);
          reject(error);
        });

        // 监听进程退出
        this.process.on("exit", (code, signal) => {
          console.log(`[PythonManager] Process exited with code ${code}, signal ${signal}`);
          this.process = null;
          this.isReady = false;
        });

        // 等待健康检查通过
        this.waitForReady()
          .then(() => {
            console.log("[PythonManager] Python backend is ready");
            resolve();
          })
          .catch((error) => {
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
  async stop(): Promise<void> {
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
      }, 5000);

      this.process!.on("exit", () => {
        clearTimeout(timeout);
        this.process = null;
        this.isReady = false;
        resolve();
      });

      // 发送 SIGTERM 进行优雅关闭
      this.process!.kill("SIGTERM");
    });
  }

  /**
   * 获取 API 基础 URL
   */
  getBaseUrl(): string {
    return this.baseUrl;
  }

  /**
   * 检查后端是否就绪
   */
  isBackendReady(): boolean {
    return this.isReady;
  }

  /**
   * 获取 Python 可执行文件路径
   */
  private getPythonExecutable(): string {
    if (app.isPackaged) {
      // 生产模式：使用打包的 Python
      const appPath = app.getAppPath();
      if (process.platform === "darwin") {
        return path.join(appPath, "Contents/MacOS/python/bin/python");
      } else if (process.platform === "win32") {
        return path.join(appPath, "python/python.exe");
      }
    }

    // 开发模式：使用系统 Python 或虚拟环境
    // 优先使用虚拟环境
    const venvPython = path.join(process.cwd(), ".venv/bin/python");
    const fs = require("fs");
    if (fs.existsSync(venvPython)) {
      return venvPython;
    }

    // 回退到系统 Python
    return process.platform === "win32" ? "python" : "python3";
  }

  /**
   * 获取应用根目录
   */
  private getAppRoot(): string {
    if (app.isPackaged) {
      return path.dirname(app.getAppPath());
    }
    return process.cwd();
  }

  /**
   * 查找可用端口
   */
  private async findAvailablePort(): Promise<number> {
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
  private isPortAvailable(port: number): Promise<boolean> {
    return new Promise((resolve) => {
      const server = http.createServer();
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
  private async waitForReady(): Promise<void> {
    const startTime = Date.now();

    while (Date.now() - startTime < this.healthCheckTimeout) {
      try {
        const isHealthy = await this.checkHealth();
        if (isHealthy) {
          return;
        }
      } catch {
        // 忽略错误，继续等待
      }

      // 等待 1 秒后重试
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }

    throw new Error("Python backend failed to start within timeout");
  }

  /**
   * 检查后端健康状态
   */
  private checkHealth(): Promise<boolean> {
    return new Promise((resolve) => {
      const req = http.request(
        {
          hostname: "127.0.0.1",
          port: this.port,
          path: "/health",
          method: "GET",
          timeout: 2000,
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
