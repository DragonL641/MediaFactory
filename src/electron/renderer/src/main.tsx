/**
 * React 应用入口
 */

import React, { useEffect, useRef } from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider, App as AntApp } from "antd";
import zhCN from "antd/locale/zh_CN";
import App from "./App";
import { wsClient } from "./api/client";
import { queryKeys } from "./api/queries";
import type { WebSocketMessage, ProgressData } from "./types";
import { appTheme } from "./theme";
import "./index.css";

// 创建 Query Client（唯一实例，配置集中管理）
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 30000,
      refetchOnWindowFocus: false,
    },
  },
});

/**
 * WebSocket Provider
 *
 * 在 App 层监听 WebSocket 消息，收到进度/任务完成时自动失效对应的 Query cache
 */
const WebSocketBridge: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const queryClientRef = useRef(queryClient);

  useEffect(() => {
    const unsubscribe = wsClient.addGlobalListener((message: WebSocketMessage) => {
      const qc = queryClientRef.current;
      const data = message.data as ProgressData | undefined;

      switch (message.type) {
        case "progress":
          // 任务进度更新 → 失效任务列表和对应任务状态
          qc.invalidateQueries({ queryKey: queryKeys.tasks });
          if (data?.task_id) {
            qc.invalidateQueries({
              queryKey: queryKeys.taskStatus(data.task_id),
            });
          }
          // 模型下载进度 → 失效模型状态
          if (data?.stage === "download") {
            qc.invalidateQueries({ queryKey: queryKeys.modelsStatus });
          }
          break;

        case "task_complete":
          // 任务完成 → 失效任务列表
          qc.invalidateQueries({ queryKey: queryKeys.tasks });
          if (data?.task_id) {
            qc.invalidateQueries({
              queryKey: queryKeys.taskStatus(data.task_id),
            });
          }
          break;

        default:
          break;
      }
    });

    return () => {
      unsubscribe();
    };
  }, []);

  return <>{children}</>;
};

// 渲染应用
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhCN} theme={appTheme}>
        <AntApp>
        <WebSocketBridge>
          <App />
        </WebSocketBridge>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
