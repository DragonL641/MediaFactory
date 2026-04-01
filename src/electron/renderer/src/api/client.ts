/**
 * API 客户端
 *
 * 使用 Axios 调用 Python FastAPI 后端
 * WebSocket 客户端用于实时进度推送
 */

import axios, { AxiosInstance, AxiosError, isAxiosError } from "axios";
import type { WebSocketMessage } from "../types";

let apiClient: AxiosInstance | null = null;
let baseUrl: string = "";

/**
 * 初始化 API 客户端
 */
export async function initApiClient(): Promise<void> {
  // 从 Electron 主进程获取 API URL
  if (window.electronAPI) {
    baseUrl = await window.electronAPI.getApiUrl();
  } else {
    // 开发模式默认
    baseUrl = "http://127.0.0.1:8765";
  }

  apiClient = axios.create({
    baseURL: baseUrl,
    timeout: 300000, // 5 分钟（长时间任务）
    headers: {
      "Content-Type": "application/json",
    },
  });

  // 请求拦截器
  apiClient.interceptors.request.use(
    (config) => {
      console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
      return config;
    },
    (error) => {
      console.error("[API] Request error:", error);
      return Promise.reject(error);
    }
  );

  // 响应拦截器
  apiClient.interceptors.response.use(
    (response) => {
      return response;
    },
    (error: AxiosError) => {
      if (error.response) {
        const data = error.response.data as Record<string, unknown>;
        const message =
          (data?.detail as string) ||
          (data?.message as string) ||
          error.message;
        console.error(`[API] Error ${error.response.status}:`, message);
      } else if (error.request) {
        console.error("[API] No response received:", error.message);
      } else {
        console.error("[API] Request config error:", error.message);
      }
      return Promise.reject(error);
    }
  );

  console.log(`[API] Client initialized with baseUrl: ${baseUrl}`);
}

/**
 * 获取 API 客户端实例
 */
export function getApiClient(): AxiosInstance {
  if (!apiClient) {
    throw new Error("API client not initialized. Call initApiClient() first.");
  }
  return apiClient;
}

/**
 * 获取 API 基础 URL
 */
export function getBaseUrl(): string {
  return baseUrl;
}

/**
 * 从 Axios 错误中提取后端返回的错误详情
 * 统一处理 detail / error / message 三种后端响应格式
 */
export function getErrorDetail(error: unknown): string | undefined {
  if (isAxiosError(error)) {
    const data = error.response?.data as Record<string, unknown> | undefined;
    if (!data) return undefined;
    return (data.detail || data.error || data.message) as string | undefined;
  }
  return undefined;
}

/**
 * WebSocket 客户端
 *
 * 用于接收后端实时进度推送，替代 HTTP 轮询
 */
export class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private baseReconnectDelay: number = 3000;
  private listeners: Map<string, Set<(data: unknown) => void>> = new Map();
  private globalListeners: Set<(data: WebSocketMessage) => void> = new Set();
  private isConnected: boolean = false;

  async connect(): Promise<void> {
    if (!baseUrl) {
      console.warn("[WS] Skipping connection - baseUrl not set");
      return;
    }

    const wsUrl = baseUrl.replace("http", "ws") + "/ws";
    const CONNECTION_TIMEOUT = 10000; // 10 秒连接超时

    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        if (this.ws) {
          this.ws.close();
        }
        reject(new Error("WebSocket connection timeout (10s)"));
      }, CONNECTION_TIMEOUT);

      try {
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          clearTimeout(timeoutId);
          console.log("[WS] Connected");
          this.reconnectAttempts = 0;
          this.isConnected = true;
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            this.handleMessage(message);
          } catch (e) {
            console.error("[WS] Failed to parse message:", event.data);
          }
        };

        this.ws.onerror = (error) => {
          clearTimeout(timeoutId);
          console.error("[WS] Error:", error);
          reject(error);
        };

        this.ws.onclose = () => {
          console.log("[WS] Disconnected");
          this.isConnected = false;
          this.attemptReconnect();
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  private handleMessage(message: WebSocketMessage): void {
    const { type, ...data } = message;

    // 通知特定事件类型的监听器
    const listeners = this.listeners.get(type);
    if (listeners) {
      listeners.forEach((callback) => callback(data));
    }

    // 通知全局监听器（用于 Query cache 失效）
    this.globalListeners.forEach((callback) => callback(message));
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay =
        this.baseReconnectDelay *
        Math.pow(2, this.reconnectAttempts - 1);
      const jitter = delay * (0.5 + Math.random() * 0.5);
      console.log(
        `[WS] Reconnecting (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${Math.round(jitter)}ms...`
      );
      setTimeout(() => this.connect(), jitter);
    }
  }

  /**
   * 订阅特定事件类型
   */
  subscribe(eventType: string, callback: (data: unknown) => void): () => void {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    this.listeners.get(eventType)!.add(callback);

    return () => {
      this.listeners.get(eventType)?.delete(callback);
    };
  }

  /**
   * 注册全局监听器，接收所有 WebSocket 消息
   * 用于在 App 层统一处理进度更新并失效 Query cache
   */
  addGlobalListener(callback: (data: WebSocketMessage) => void): () => void {
    this.globalListeners.add(callback);
    return () => {
      this.globalListeners.delete(callback);
    };
  }

  send(type: string, data: Record<string, unknown> = {}): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, ...data }));
    }
  }

  subscribeToTask(
    taskId: string,
    callback: (progress: unknown) => void
  ): () => void {
    this.send("subscribe", { task_id: taskId });
    return this.subscribe("progress", (data) => {
      const progressData = data as Record<string, unknown>;
      if (progressData.task_id === taskId) {
        callback(progressData.data);
      }
    });
  }

  disconnect(): void {
    this.listeners.clear();
    this.globalListeners.clear();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  getConnectionState(): boolean {
    return this.isConnected;
  }
}

// 导出单例
export const wsClient = new WebSocketClient();
