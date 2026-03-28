/**
 * 两步任务创建对话框
 *
 * Step 1: 选择任务类型
 * Step 2: 配置任务参数（根据类型显示不同表单）
 */

import React, { useState } from "react";
import { Modal, Steps, App, Form, Button } from "antd";
import { useTranslation } from "react-i18next";
import TaskTypeSelector, { useTaskTypes } from "./TaskTypeSelector";
import SubtitleForm from "./forms/SubtitleForm";
import AudioForm from "./forms/AudioForm";
import TranscribeForm from "./forms/TranscribeForm";
import TranslateForm from "./forms/TranslateForm";
import EnhanceForm from "./forms/EnhanceForm";
import {
  useCreateSubtitleTaskMutation,
  useCreateAudioTaskMutation,
  useCreateTranscribeTaskMutation,
  useCreateTranslateTaskMutation,
  useCreateEnhanceTaskMutation,
} from "../../api/queries";

interface CreateTaskDialogProps {
  open: boolean;
  onClose: () => void;
}

/**
 * Step 1 表单区域，拥有 form 实例（仅在 Step 1 渲染，避免 useForm 未连接警告）
 */
const TaskConfigStep: React.FC<{
  selectedType: string;
  onSuccess: () => void;
  onSubmitRef: React.MutableRefObject<(() => Promise<void>) | undefined>;
  onSubmittingChange: (v: boolean) => void;
}> = ({ selectedType, onSuccess, onSubmitRef, onSubmittingChange }) => {
  const [form] = Form.useForm();
  const { message } = App.useApp();
  const { t } = useTranslation("tasks");
  const taskTypes = useTaskTypes();

  const subtitleMutation = useCreateSubtitleTaskMutation();
  const audioMutation = useCreateAudioTaskMutation();
  const transcribeMutation = useCreateTranscribeTaskMutation();
  const translateMutation = useCreateTranslateTaskMutation();
  const enhanceMutation = useCreateEnhanceTaskMutation();

  const isSubmitting =
    subtitleMutation.isPending ||
    audioMutation.isPending ||
    transcribeMutation.isPending ||
    translateMutation.isPending ||
    enhanceMutation.isPending;

  React.useEffect(() => {
    onSubmittingChange(isSubmitting);
  }, [isSubmitting, onSubmittingChange]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const mutations: Record<string, any> = {
        subtitle: subtitleMutation,
        audio: audioMutation,
        transcribe: transcribeMutation,
        translate: translateMutation,
        enhance: enhanceMutation,
      };

      mutations[selectedType]?.mutate(values, {
        onSuccess: () => {
          message.success(t("tasks:createDialog.created"));
          onSuccess();
        },
      });
    } catch {
      // 表单验证失败
    }
  };

  React.useEffect(() => {
    onSubmitRef.current = handleSubmit;
  }, [selectedType, isSubmitting]);

  const selectedTypeInfo = taskTypes.find((t) => t.key === selectedType);

  const renderForm = () => {
    switch (selectedType) {
      case "subtitle":
        return <SubtitleForm form={form} />;
      case "audio":
        return <AudioForm form={form} />;
      case "transcribe":
        return <TranscribeForm form={form} />;
      case "translate":
        return <TranslateForm form={form} />;
      case "enhance":
        return <EnhanceForm form={form} />;
      default:
        return null;
    }
  };

  return (
    <>
      <Steps
        current={1}
        size="small"
        style={{ marginBottom: 24 }}
        items={[
          { title: t("tasks:createDialog.steps.selectType") },
          { title: selectedTypeInfo?.title || t("tasks:createDialog.steps.configure") },
        ]}
      />
      {renderForm()}
    </>
  );
};

const CreateTaskDialog: React.FC<CreateTaskDialogProps> = ({ open, onClose }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const handleSubmitRef = React.useRef<(() => Promise<void>) | undefined>();
  const { t } = useTranslation("tasks");

  const handleClose = () => {
    setCurrentStep(0);
    setSelectedType(null);
    onClose();
  };

  const handleSubmit = async () => {
    if (handleSubmitRef.current) {
      await handleSubmitRef.current();
    }
  };

  return (
    <Modal
      title={t("tasks:createDialog.title")}
      open={open}
      onCancel={handleClose}
      width={640}
      footer={
        currentStep === 0
          ? null
          : [
              <Button
                key="back"
                onClick={() => setCurrentStep(0)}
              >
                {t("common:actions.back")}
              </Button>,
              <Button
                key="submit"
                type="primary"
                onClick={handleSubmit}
                disabled={isSubmitting}
              >
                {isSubmitting ? t("common:actions.creating") : t("tasks:createDialog.create")}
              </Button>,
            ]
      }
      destroyOnHidden
    >
      {currentStep === 0 ? (
        <TaskTypeSelector onSelect={(key) => { setSelectedType(key); setCurrentStep(1); }} />
      ) : selectedType ? (
        <TaskConfigStep
          selectedType={selectedType}
          onSuccess={handleClose}
          onSubmitRef={handleSubmitRef}
          onSubmittingChange={setIsSubmitting}
        />
      ) : null}
    </Modal>
  );
};

export default CreateTaskDialog;
