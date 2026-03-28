/**
 * LLM Config 页面
 *
 * 管理 LLM 供应商配置：添加、编辑、删除、测试连接
 * 对标 Flet 的 llm_config.py
 */

import React, { useState } from "react";
import { Button, Space, Spin, App, theme, Skeleton, Card, Result } from "antd";
import { PlusOutlined, CloudOutlined } from "@ant-design/icons";
import {
  useLLMPresetsQuery,
  useTestAllLLMMutation,
} from "../../api/queries";
import type { LLMPresetInfo } from "../../types";
import PageHeader from "../../components/Layout/PageHeader";
import { EmptyState } from "../../components/common";
import ProviderCard from "./ProviderCard";
import ProviderDialog from "./ProviderDialog";

const LLMConfigPage: React.FC = () => {
  const { token } = theme.useToken();
  const { message } = App.useApp();
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
        message.success("All connections tested");
        refetch();
      },
    });
  };

  if (isLoading) {
    return (
      <div className="page-enter">
        <PageHeader title="LLM Providers" />
        <Card style={{ marginBottom: 12 }}><Skeleton active paragraph={{ rows: 1 }} /></Card>
        <Card style={{ marginBottom: 12 }}><Skeleton active paragraph={{ rows: 1 }} /></Card>
      </div>
    );
  }

  if (isError) {
    return (
      <div style={{ padding: 48 }}>
        <Result
          status="error"
          title="Failed to load LLM configuration"
          subTitle="Unable to connect to the backend service"
          extra={
            <Button type="primary" onClick={() => refetch()}>
              Retry
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className="page-enter">
      <PageHeader
        title="LLM Providers"
        description="Configure API credentials for your LLM providers"
        actions={
          <Space size={8}>
            {configuredPresets.length > 0 && (
              <Button
                onClick={handleTestAll}
                loading={testAllMutation.isPending}
              >
                Test All
              </Button>
            )}
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleAdd}
            >
              Add Provider
            </Button>
          </Space>
        }
      />

      {configuredPresets.length === 0 ? (
        <EmptyState
          icon={<CloudOutlined />}
          title="No providers configured"
          description="Add a LLM provider to enable AI-powered translation"
          actionText="Add Provider"
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
