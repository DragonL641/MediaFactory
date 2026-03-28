/**
 * LLM Config 页面
 *
 * 管理 LLM 供应商配置：添加、编辑、删除、测试连接
 * 对标 Flet 的 llm_config.py
 */

import React, { useState } from "react";
import { Button, Space, App, theme, Result } from "antd";
import { PlusOutlined, CloudOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import {
  useLLMPresetsQuery,
  useTestAllLLMMutation,
} from "../../api/queries";
import type { LLMPresetInfo } from "../../types";
import PageHeader from "../../components/Layout/PageHeader";
import { EmptyState, PageSkeleton } from "../../components/common";
import ProviderCard from "./ProviderCard";
import ProviderDialog from "./ProviderDialog";

const LLMConfigPage: React.FC = () => {
  const { token } = theme.useToken();
  const { message } = App.useApp();
  const { t } = useTranslation("llmConfig");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingPresetId, setEditingPresetId] = useState<string | null>(null);

  const {
    data: presets,
    isLoading,
    isError,
    refetch,
  } = useLLMPresetsQuery();
  const testAllMutation = useTestAllLLMMutation();

  // 过滤出已配置的供应商
  const configuredPresets = presets
    ? (Object.entries(presets) as [string, LLMPresetInfo][])
        .filter(([, info]) => info.configured && info.has_api_key)
        .map(([id, info]) => ({
          id,
          displayName: info.display_name,
          baseUrl: info.base_url,
          model: info.model || info.model_examples?.[0] || "",
          hasApiKey: info.has_api_key,
          connectionAvailable: info.connection_available,
        }))
    : [];

  const handleAdd = () => {
    setEditingPresetId(null);
    setDialogOpen(true);
  };

  const handleEdit = (presetId: string) => {
    setEditingPresetId(presetId);
    setDialogOpen(true);
  };

  const handleDialogSuccess = () => {
    refetch();
  };

  const handleTestAll = () => {
    testAllMutation.mutate(undefined, {
      onSuccess: () => {
        message.success(t("llmConfig:messages.allTested"));
        refetch();
      },
    });
  };

  if (isLoading) {
    return <PageSkeleton type="llm" />;
  }

  if (isError) {
    return (
      <div style={{ padding: 48 }}>
        <Result
          status="error"
          title={t("llmConfig:error.loadFailed")}
          subTitle={t("common:error.connectFailed")}
          extra={
            <Button type="primary" onClick={() => refetch()}>
              {t("common:error.retry")}
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className="page-enter">
      <PageHeader
        title={t("llmConfig:pageHeader.title")}
        description={t("llmConfig:pageHeader.description")}
        actions={
          <Space size={8}>
            {configuredPresets.length > 0 && (
              <Button
                onClick={handleTestAll}
                loading={testAllMutation.isPending}
              >
                {t("llmConfig:actions.testAll")}
              </Button>
            )}
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleAdd}
            >
              {t("llmConfig:actions.addProvider")}
            </Button>
          </Space>
        }
      />

      {configuredPresets.length === 0 ? (
        <EmptyState
          icon={<CloudOutlined />}
          title={t("llmConfig:empty.title")}
          description={t("llmConfig:empty.description")}
          actionText={t("llmConfig:empty.actionText")}
          onAction={handleAdd}
        />
      ) : (
        <div>
          {configuredPresets.map((preset) => (
            <ProviderCard
              key={preset.id}
              presetId={preset.id}
              displayName={preset.displayName}
              baseUrl={preset.baseUrl}
              model={preset.model}
              hasApiKey={preset.hasApiKey}
              connectionAvailable={preset.connectionAvailable}
              onEdit={() => handleEdit(preset.id)}
            />
          ))}
        </div>
      )}

      <ProviderDialog
        open={dialogOpen}
        editingPresetId={editingPresetId}
        onClose={() => {
          setDialogOpen(false);
          setEditingPresetId(null);
        }}
        onSuccess={handleDialogSuccess}
      />
    </div>
  );
};

export default LLMConfigPage;
