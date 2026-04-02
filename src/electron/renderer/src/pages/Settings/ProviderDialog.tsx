/**
 * LLM 供应商配置对话框
 *
 * 从 LLMConfig/ProviderDialog 迁移，支持添加和编辑 LLM 供应商配置
 */

import React, { useEffect, useMemo, useState } from "react";
import { Modal, Form, Input, Select, App, theme } from "antd";
import { useTranslation } from "react-i18next";
import { useLLMPresetsQuery, useUpdateLLMPresetMutation } from "../../api/queries";
import { getErrorDetail } from "../../api/client";
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
  const { token } = theme.useToken();
  const { t } = useTranslation("llmConfig");
  const isEditing = !!editingPresetId;

  const { data: presets, isLoading: presetsLoading } = useLLMPresetsQuery();
  const updateMutation = useUpdateLLMPresetMutation();

  const handlePresetChange = (presetId: string) => {
    if (presets && presets[presetId]) {
      form.setFieldsValue({ base_url: presets[presetId].base_url });
    }
  };

  useEffect(() => {
    if (open && editingPresetId && presets) {
      const preset = presets[editingPresetId];
      if (preset) {
        form.setFieldsValue({
          preset_id: editingPresetId,
          base_url: preset.base_url,
          api_key: "",
          model: preset.model || "",
        });
        setSelectedProvider(editingPresetId);
      }
    } else if (open && !editingPresetId) {
      form.resetFields();
      setSelectedProvider(undefined);
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
              isEditing ? t("messages.providerUpdated") : t("messages.providerAdded")
            );
            onSuccess();
            onClose();
            form.resetFields();
          },
          onError: (error: unknown) => {
            message.error(getErrorDetail(error) || t("messages.saveFailed"));
          },
        }
      );
    } catch {
      // 表单验证失败
    }
  };

  const presetOptions = useMemo(() => {
    return (Object.entries(presets || {}) as [string, LLMPresetInfo][]).map(
      ([id, info]) => ({ value: id, label: info.display_name })
    );
  }, [presets]);

  const [selectedProvider, setSelectedProvider] = useState<string>();

  return (
    <Modal
      title={isEditing ? t("dialog.editTitle") : t("dialog.addTitle")}
      open={open}
      onOk={handleSubmit}
      onCancel={onClose}
      confirmLoading={updateMutation.isPending}
      width={420}
    >
      <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
        <Form.Item
          name="preset_id"
          label={t("dialog.provider")}
          rules={[{ required: true, message: t("dialog.providerRequired") }]}
        >
          <Select
            placeholder={t("dialog.selectProvider")}
            disabled={isEditing}
            onChange={(val) => {
              setSelectedProvider(val);
              handlePresetChange(val);
            }}
            loading={presetsLoading}
            options={presetOptions}
          />
        </Form.Item>

        <Form.Item
          name="base_url"
          label={t("dialog.baseUrl")}
          rules={[{ required: true, message: t("dialog.baseUrlRequired") }]}
        >
          <Input
            placeholder={
              selectedProvider === "custom"
                ? "http://localhost:11434/v1"
                : "https://api.example.com/v1"
            }
          />
        </Form.Item>

        <Form.Item
          name="api_key"
          label={t("dialog.apiKey")}
          rules={[
            {
              required: selectedProvider !== "custom",
              message: t("dialog.apiKeyRequired"),
            },
          ]}
        >
          <>
            <Input.Password
              placeholder={
                selectedProvider === "custom"
                  ? t("dialog.apiKeyOptional")
                  : "sk-..."
              }
            />
            {selectedProvider === "custom" && (
              <span style={{ fontSize: 12, color: token.colorTextSecondary }}>
                {t("dialog.localLlmNoApiKey")}
              </span>
            )}
          </>
        </Form.Item>

        <Form.Item
          name="model"
          label={t("dialog.model")}
          rules={[{ required: true, message: t("dialog.modelRequired") }]}
        >
          <Input placeholder="e.g., gpt-4o-mini, deepseek-chat" />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default ProviderDialog;
