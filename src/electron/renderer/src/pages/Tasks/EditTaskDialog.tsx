/**
 * 编辑任务对话框
 *
 * 根据 task_type 显示对应的可编辑字段，
 * task_type 和 input_path 不可修改。
复用各任务类型的 FormFields 组件，与创建表单保持一致
 */

import React, { useEffect } from "react";
import { Modal, Form, Input, App, Spin } from "antd";
import { useTranslation } from "react-i18next";
import { useTaskConfigQuery, useUpdateTaskConfigMutation } from "../../api/queries";
import { getErrorDetail } from "../../api/client";
import { TaskType } from "../../types";
import SubtitleFormFields from "./forms/SubtitleFormFields";
import AudioFormFields from "./forms/AudioFormFields";
import TranscribeFormFields from "./forms/TranscribeFormFields";
import TranslateFormFields from "./forms/TranslateFormFields";
import EnhanceFormFields from "./forms/EnhanceFormFields";

const TASK_TYPE_LABEL_KEYS: Record<string, string> = {
  [TaskType.SUBTITLE]: "tasks:typeLabels.subtitle",
  [TaskType.AUDIO]: "tasks:typeLabels.audio",
  [TaskType.TRANSCRIBE]: "tasks:typeLabels.transcribe",
  [TaskType.TRANSLATE]: "tasks:typeLabels.translate",
  [TaskType.ENHANCE]: "tasks:typeLabels.enhance",
};

interface EditTaskDialogProps {
  taskId: string;
  open: boolean;
  onClose: () => void;
}

const EditTaskDialog: React.FC<EditTaskDialogProps> = ({
  taskId,
  open,
  onClose,
}) => {
  const [form] = Form.useForm();
  const { message } = App.useApp();
  const { t } = useTranslation("tasks");
  const { data: config, isLoading } = useTaskConfigQuery(taskId);
  const updateMutation = useUpdateTaskConfigMutation();

  useEffect(() => {
    if (config && open) {
      // 将嵌套子模型展平为表单字段
      const flat: Record<string, unknown> = { ...config };
      if (config.audio_config) {
        Object.entries(config.audio_config).forEach(([k, v]) => {
          flat[`audio_${k}`] = v;
        });
        delete flat.audio_config;
      }
      if (config.subtitle_config) {
        // SubtitleFormFields 不使用前缀，直接展平到根级别
        Object.entries(config.subtitle_config).forEach(([k, v]) => {
          flat[k] = v;
        });
        delete flat.subtitle_config;
      }
      if (config.enhancement_config) {
        Object.entries(config.enhancement_config).forEach(([k, v]) => {
          flat[`enhancement_${k === "model" ? "model_type" : k}`] = v;
        });
        delete flat.enhancement_config;
      }
      form.setFieldsValue(flat);
    }
  }, [config, form, open]);

  useEffect(() => {
    if (!open) {
      form.resetFields();
    }
  }, [open, form]);

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      // 将展平的表单字段重新组装为嵌套结构
      const nested: Record<string, unknown> = {};
      const audioKeys = ["sample_rate", "channels", "filter_enabled", "highpass_freq", "lowpass_freq", "volume", "output_format"];
      const subtitleKeys = ["output_format", "bilingual", "bilingual_layout", "style_preset"];
      const enhancementKeys = ["scale", "model_type", "denoise", "temporal"];

      Object.entries(values).forEach(([key, value]) => {
        if (key.startsWith("audio_")) {
          const subKey = key.replace("audio_", "");
          if (!nested.audio_config) nested.audio_config = {};
          (nested.audio_config as Record<string, unknown>)[subKey] = value;
        } else if (key.startsWith("enhancement_")) {
          const subKey = key.replace("enhancement_", "");
          if (subKey === "model_type") {
            if (!nested.enhancement_config) nested.enhancement_config = {};
            (nested.enhancement_config as Record<string, unknown>).model = value;
          } else {
            if (!nested.enhancement_config) nested.enhancement_config = {};
            (nested.enhancement_config as Record<string, unknown>)[subKey] = value;
          }
        } else if (subtitleKeys.includes(key)) {
          // 字幕字段归入 subtitle_config
          if (!nested.subtitle_config) nested.subtitle_config = {};
          (nested.subtitle_config as Record<string, unknown>)[key] = value;
        } else {
          nested[key] = value;
        }
      });

      await updateMutation.mutateAsync({ taskId, config: nested });
      message.success(t("editDialog.saved"));
      close();
    } catch (error: unknown) {
      const detail = getErrorDetail(error);
      if (detail) {
        message.error(detail);
      }
    }
  };

  const renderFormFields = () => {
    if (!config) return null;
    const taskType = config.task_type as TaskType;

    switch (taskType) {
      case TaskType.SUBTITLE:
        return <SubtitleFormFields form={form} />;
      case TaskType.AUDIO:
        return <AudioFormFields form={form} fieldPrefix="audio_" />;
      case TaskType.TRANSCRIBE:
        return <TranscribeFormFields form={form} />;
      case TaskType.TRANSLATE:
        return <TranslateFormFields form={form} />;
      case TaskType.ENHANCE:
        return <EnhanceFormFields fieldPrefix="enhancement_" />;
      default:
        return null;
    }
  };

  return (
    <Modal
      title={t("editDialog.title")}
      open={open}
      onCancel={onClose}
      onOk={handleOk}
      confirmLoading={updateMutation.isPending}
      destroyOnHidden
    >
      {isLoading ? (
        <div style={{ textAlign: "center", padding: 24 }}>
          <Spin />
        </div>
      ) : (
        <Form form={form} layout="vertical">
          <Form.Item label={t("editDialog.taskType")}>
            <Input value={t(TASK_TYPE_LABEL_KEYS[config?.task_type] || config?.task_type) || config?.task_type} disabled />
          </Form.Item>
          <Form.Item label={t("editDialog.inputFile")}>
            <Input value={config?.input_path} disabled />
          </Form.Item>
          {renderFormFields()}
        </Form>
      )}
    </Modal>
  );
};

export default EditTaskDialog;
