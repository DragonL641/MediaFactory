/**
 * React 应用入口
 */

import React, { useEffect, useRef, useState } from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider, App as AntApp } from "antd";
import zhCN from "antd/locale/zh_CN";
import enUS from "antd/locale/en_US";
import App from "./App";
import { wsClient } from "./api/client";
import { queryKeys } from "./api/queries";
import type { WebSocketMessage, ProgressData } from "./types";
import { appTheme } from "./theme";
import i18n from "i18next";
import "./i18n";
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

// 全局 Message 配置：右上角、短暂显示
const messageConfig = {
  top: 64,
  duration: 2.5,
  maxCount: 3,
};

// Ant Design locale 映射
const ANT_LOCALES: Record<string, typeof enUS> = {
  en: enUS,
  "zh-CN": zhCN,
};

// 动态 locale 包装组件
const AppWithLocale: React.FC = () => {
  const [antdLocale, setAntdLocale] = useState<typeof enUS>(zhCN);

  useEffect(() => {
    // 监听 i18next 语言变化，同步 Ant Design locale
    const handleChange = (lng: string) => {
      setAntdLocale(ANT_LOCALES[lng] || enUS);
    };

    // 设置初始 locale
    handleChange(i18n.language || "en");
    i18n.on("languageChanged", handleChange);

    return () => {
      i18n.off("languageChanged", handleChange);
    };
  }, []);

  return (
    <ConfigProvider locale={antdLocale} theme={appTheme}>
      <AntApp message={messageConfig}>
        <WebSocketBridge>
          <App />
        </WebSocketBridge>
      </AntApp>
    </ConfigProvider>
  );
};

// 渲染应用
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <AppWithLocale />
    </QueryClientProvider>
  </React.StrictMode>
);
