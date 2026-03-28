/**
 * LLM 供应商配置对话框
 *
 * 支持添加和编辑 LLM 供应商配置
 */

import React, { useEffect, useState } from "react";
import {
  Modal,
  Form,
  Input,
  Select,
  App,
} from "antd";
import { useTranslation } from "react-i18next";
import { useLLMPresetsQuery, useUpdateLLMPresetMutation } from "../../api/queries";
import { isAxiosError } from "axios";
import type { LLMPresetInfo } from "../../types";

interface ProviderDialogProps {
  open: boolean;
  editingPresetId: string | null;
  onClose: () => void;
  onSuccess: () => void;
}

const ProviderDialog: React.FC<ProviderDialogProps> = ({
  open,
  editingPresetId,
  onClose,
  onSuccess,
}) => {
  const [form] = Form.useForm();
  const { message } = App.useApp();
  const { t } = useTranslation("llmConfig");
  const isEditing = !!editingPresetId;

  const { data: presets, isLoading: presetsLoading } = useLLMPresetsQuery();
  const updateMutation = useUpdateLLMPresetMutation();

  // 预设选择变化时自动填充 base_url
  const handlePresetChange = (presetId: string) => {
    if (presets && presets[presetId]) {
      form.setFieldsValue({
        base_url: presets[presetId].base_url,
      });
    }
  };

  // 编辑模式：初始化表单
  useEffect(() => {
    if (open && editingPresetId && presets) {
      const preset = presets[editingPresetId];
      if (preset) {
        form.setFieldsValue({
          preset_id: editingPresetId,
          base_url: preset.base_url,
          api_key: "", // 不回填 API Key
          model: preset.model || "",
        });
      }
    } else if (open && !editingPresetId) {
      form.resetFields();
    }
  }, [open, editingPresetId, presets, form]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      updateMutation.mutate(
        {
          presetId: values.preset_id,
          api_key: values.api_key,
          base_url: values.base_url,
          model: values.model,
        },
        {
          onSuccess: () => {
            message.success(
              isEditing
                ? t("llmConfig:messages.providerUpdated")
                : t("llmConfig:messages.providerAdded")
            );
            onSuccess();
            onClose();
            form.resetFields();
          },
          onError: (error: unknown) => {
            const detail = isAxiosError(error) ? error.response?.data?.detail : undefined;
            message.error(
              detail || t("llmConfig:messages.saveFailed")
            );
          },
        }
      );
    } catch {
      // 表单验证失败
    }
  };

  // 构建预设选项（排除 custom，编辑模式禁用选择）
  const presetOptions = (Object.entries(presets || {}) as [string, LLMPresetInfo][])
    .filter(([id]) => id !== "custom")
    .map(([id, info]) => ({
      value: id,
      label: info.display_name,
    }));

  return (
    <Modal
      title={isEditing ? t("llmConfig:dialog.editTitle") : t("llmConfig:dialog.addTitle")}
      open={open}
      onOk={handleSubmit}
      onCancel={onClose}
      confirmLoading={updateMutation.isPending}
      destroyOnHidden
    >
      <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
        <Form.Item
          name="preset_id"
          label={t("llmConfig:dialog.provider")}
          rules={[{ required: true, message: t("llmConfig:dialog.providerRequired") }]}
        >
          <Select
            placeholder={t("llmConfig:dialog.selectProvider")}
            disabled={isEditing}
            onChange={handlePresetChange}
            loading={presetsLoading}
            options={presetOptions}
          />
        </Form.Item>

        <Form.Item
          name="base_url"
          label={t("llmConfig:dialog.baseUrl")}
          rules={[{ required: true, message: t("llmConfig:dialog.baseUrlRequired") }]}
        >
          <Input placeholder="https://api.example.com/v1" />
        </Form.Item>

        <Form.Item
          name="api_key"
          label={t("llmConfig:dialog.apiKey")}
          rules={[{ required: true, message: t("llmConfig:dialog.apiKeyRequired") }]}
        >
          <Input.Password placeholder="sk-..." />
        </Form.Item>

        <Form.Item
          name="model"
          label={t("llmConfig:dialog.model")}
          rules={[{ required: true, message: t("llmConfig:dialog.modelRequired") }]}
        >
          <Input placeholder="e.g., gpt-4o-mini, deepseek-chat" />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default ProviderDialog;
