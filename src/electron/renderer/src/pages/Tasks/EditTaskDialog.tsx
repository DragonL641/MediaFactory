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
      form.setFieldsValue(config);
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
      await updateMutation.mutateAsync({ taskId, config: values });
      message.success(t("editDialog.saved"));
      onClose();
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
        return <AudioFormFields fieldPrefix="audio_" />;
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
