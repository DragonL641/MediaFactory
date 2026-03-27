/**
 * LLM 供应商卡片组件
 *
 * 显示单个供应商的配置信息和操作按钮
 */

import React, { useState } from "react";
import {
  Card,
  Tag,
  Button,
  Space,
  Popconfirm,
  Typography,
  Tooltip,
  App,
} from "antd";
import {
  EditOutlined,
  DeleteOutlined,
  WifiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from "@ant-design/icons";
import { useTestLLMMutation, useDeleteLLMPresetMutation } from "../../api/queries";
import { isAxiosError } from "axios";
import type { TestConnectionResponse } from "../../types";

const { Text } = Typography;

interface ProviderCardProps {
  presetId: string;
  displayName: string;
  baseUrl: string;
  model: string;
  hasApiKey: boolean;
  connectionAvailable?: boolean;
  onEdit: () => void;
}

const ProviderCard: React.FC<ProviderCardProps> = ({
  presetId,
  displayName,
  baseUrl,
  model,
  hasApiKey,
  connectionAvailable,
  onEdit,
}) => {
  const [testing, setTesting] = useState(false);
  const testMutation = useTestLLMMutation();
  const deleteMutation = useDeleteLLMPresetMutation();
  const { message } = App.useApp();

  const handleTest = async () => {
    setTesting(true);
    testMutation.mutate(presetId, {
      onSuccess: (data: TestConnectionResponse) => {
        setTesting(false);
        if (data.success) {
          message.success(`${displayName}: Connected (${data.latency_ms}ms)`);
        } else {
          message.error(`${displayName}: ${data.error || "Connection failed"}`);
        }
      },
      onError: (error: unknown) => {
        setTesting(false);
        const errorDetail = isAxiosError(error) ? error.response?.data?.error : undefined;
        const errorMessage = error instanceof Error ? error.message : "Test failed";
        message.error(`${displayName}: ${errorDetail || errorMessage}`);
      },
    });
  };

  const handleDelete = () => {
    deleteMutation.mutate(presetId);
  };

  return (
    <Card
      size="small"
      style={{ marginBottom: 12 }}
      extra={
        <Space size={4}>
          <Tooltip title="Test Connection">
            <Button
              type="text"
              size="small"
              icon={<WifiOutlined />}
              loading={testing}
              onClick={handleTest}
            />
          </Tooltip>
          <Tooltip title="Edit">
            <Button type="text" size="small" icon={<EditOutlined />} onClick={onEdit} />
          </Tooltip>
          <Popconfirm
            title="Delete this provider?"
            description="This will clear the API key and model configuration."
            onConfirm={handleDelete}
            okText="Delete"
            cancelText="Cancel"
            okButtonProps={{ danger: true }}
          >
            <Tooltip title="Delete">
              <Button type="text" size="small" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      }
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <Text strong>{displayName}</Text>
          <br />
          <Text type="secondary" style={{ fontSize: 12 }}>
            {baseUrl}
          </Text>
          {model && (
            <>
              <br />
              <Text type="secondary" style={{ fontSize: 12 }}>
                Model: {model}
              </Text>
            </>
          )}
        </div>
        {connectionAvailable !== undefined && (
          <Tag
            icon={
              connectionAvailable ? (
                <CheckCircleOutlined />
              ) : (
                <CloseCircleOutlined />
              )
            }
            color={connectionAvailable ? "success" : "default"}
          >
            {connectionAvailable ? "Connected" : "Not Connected"}
          </Tag>
        )}
      </div>
    </Card>
  );
};

export default ProviderCard;
