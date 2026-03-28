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
import { useTranslation } from "react-i18next";
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
  const { t } = useTranslation("llmConfig");

  const handleTest = async () => {
    setTesting(true);
    testMutation.mutate(presetId, {
      onSuccess: (data: TestConnectionResponse) => {
        setTesting(false);
        if (data.success) {
          message.success(t("llmConfig:card.connectedMsg", { name: displayName, latency: data.latency_ms }));
        } else {
          message.error(`${displayName}: ${data.error || t("llmConfig:card.connectionFailed")}`);
        }
      },
      onError: (error: unknown) => {
        setTesting(false);
        const errorDetail = isAxiosError(error) ? error.response?.data?.error : undefined;
        const errorMessage = error instanceof Error ? error.message : t("llmConfig:card.testFailed");
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
          {model && <div className="provider-card-model">{t("llmConfig:card.model", { model })}</div>}
        </div>
        <div className="provider-card-actions">
          {connectionAvailable !== undefined && (
            <StatusTag
              status={connectionAvailable ? "success" : "default"}
              text={connectionAvailable ? t("llmConfig:card.connected") : t("llmConfig:card.notConnected")}
            />
          )}
          <Tooltip title={t("llmConfig:card.testTooltip")}>
            <Button
              type="text"
              size="small"
              icon={<WifiOutlined />}
              loading={testing}
              onClick={handleTest}
            />
          </Tooltip>
          <Tooltip title={t("llmConfig:card.editTooltip")}>
            <Button type="text" size="small" icon={<EditOutlined />} onClick={onEdit} />
          </Tooltip>
          <Popconfirm
            title={t("llmConfig:confirm.deleteTitle")}
            description={t("llmConfig:confirm.deleteDescription")}
            onConfirm={handleDelete}
            okText={t("common:actions.delete")}
            cancelText={t("common:actions.cancel")}
            okButtonProps={{ danger: true }}
          >
            <Tooltip title={t("llmConfig:card.deleteTooltip")}>
              <Button type="text" size="small" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </div>
      </div>
    </div>
  );
};

export default ProviderCard;
