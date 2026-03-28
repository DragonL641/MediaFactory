/**
 * LLM 供应商卡片组件
 *
 * 显示单个供应商的配置信息和操作按钮
 */

import React, { useState } from "react";
import {
  Button,
  Popconfirm,
  Tooltip,
  App,
} from "antd";
import {
  EditOutlined,
  DeleteOutlined,
  WifiOutlined,
} from "@ant-design/icons";
import { useTestLLMMutation, useDeleteLLMPresetMutation } from "../../api/queries";
import { isAxiosError } from "axios";
import type { TestConnectionResponse } from "../../types";
import { StatusTag } from "../../components/common";

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
    <div className="provider-card">
      <div className="provider-card-header">
        <div className="provider-card-info">
          <div className="provider-card-name">{displayName}</div>
          <div className="provider-card-url">{baseUrl}</div>
          {model && <div className="provider-card-model">Model: {model}</div>}
        </div>
        <div className="provider-card-actions">
          {connectionAvailable !== undefined && (
            <StatusTag
              status={connectionAvailable ? "success" : "default"}
              text={connectionAvailable ? "Connected" : "Not Connected"}
            />
          )}
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
        </div>
      </div>
    </div>
  );
};

export default ProviderCard;
