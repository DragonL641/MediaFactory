/**
 * React 根组件
 */

import React, { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Spin, Typography, theme } from "antd";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import MainLayout from "./components/Layout/MainLayout";
import ErrorBoundary from "./components/ErrorBoundary";
import TasksPage from "./pages/Tasks";
import ModelsPage from "./pages/Models";
import LLMConfigPage from "./pages/LLMConfig";
import SettingsPage from "./pages/Settings";
import { initApiClient, wsClient } from "./api/client";
import { queryKeys } from "./api/queries";
import type { WebSocketMessage } from "./types";

const { Text } = Typography;

const App: React.FC = () => {
  const { token } = theme.useToken();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const { t } = useTranslation("common");

  useEffect(() => {
    const init = async () => {
      try {
        await initApiClient();
        // 初始化 WebSocket 连接
        wsClient.connect();
        // 注册全局监听器，收到进度/完成消息时刷新任务列表
        wsClient.addGlobalListener((message: WebSocketMessage) => {
          if (message.type === "progress" || message.type === "task_complete") {
            queryClient.invalidateQueries({ queryKey: queryKeys.tasks });
          }
        });

        // 从后端获取语言偏好
        const client = (await import("./api/client")).getApiClient;
        try {
          const apiClient = client();
          const configRes = await apiClient.get("/api/config/");
          const lang = configRes.data?.app?.language || "en";
          const i18n = (await import("i18next")).default;
          await i18n.changeLanguage(lang);
        } catch {
          // 使用默认语言
        }

        setIsLoading(false);
      } catch (err) {
        console.error("Failed to initialize API client:", err);
        setError(err instanceof Error ? err.message : "Failed to connect");
        setIsLoading(false);
      }
    };

    init();
  }, []);

  if (isLoading) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
        }}
      >
        <Spin size="large">
          <div style={{ padding: 24, textAlign: "center" }}>
            {t("loading.connecting")}
          </div>
        </Spin>
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
          padding: 24,
        }}
      >
        <h2>{t("loading.connectError")}</h2>
        <Text type="secondary">{error}</Text>
        <br />
        <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
          {t("loading.connectHint")}
        </Text>
      </div>
    );
  }

  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <MainLayout>
        <ErrorBoundary>
        <Routes>
          <Route path="/" element={<Navigate to="/tasks" replace />} />
          <Route path="/tasks" element={<TasksPage />} />
          <Route path="/models" element={<ModelsPage />} />
          <Route path="/llm-config" element={<LLMConfigPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
        </ErrorBoundary>
      </MainLayout>
    </BrowserRouter>
  );
};

export default App;
