/**
 * LLM Config 页面
 *
 * 管理 LLM 供应商配置：添加、编辑、删除、测试连接
 * 对标 Flet 的 llm_config.py
 */

import React, { useState } from "react";
import { Button, Typography, Empty, Spin, App, theme, Skeleton, Card, Result } from "antd";
import { PlusOutlined, CloudOutlined } from "@ant-design/icons";
import {
  useLLMPresetsQuery,
  useTestAllLLMMutation,
} from "../../api/queries";
import type { LLMPresetInfo } from "../../types";
import PageHeader from "../../components/Layout/PageHeader";
import ProviderCard from "./ProviderCard";
import ProviderDialog from "./ProviderDialog";

const { Title, Text } = Typography;

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
        actions={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleAdd}
          >
            Add Provider
          </Button>
        }
      />

      {configuredPresets.length === 0 ? (
        <Empty
          image={<CloudOutlined style={{ fontSize: 48, color: token.colorTextQuaternary }} />}
          description={
            <span>
              No LLM providers configured
              <br />
              <Text type="secondary">
                Click "Add Provider" to configure a remote LLM API
              </Text>
            </span>
          }
        />
      ) : (
        <>
          <div style={{ marginBottom: 16 }}>
            <Button
              size="small"
              onClick={handleTestAll}
              loading={testAllMutation.isPending}
            >
              Test All Connections
            </Button>
          </div>
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
        </>
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
