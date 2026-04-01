/**
 * 两步任务创建对话框
 *
 * Step 1: 选择任务类型（5 个选项卡片）
 * Step 2: 配置任务参数（带步骤指示器）
 * Soft Bento 风格：圆角 Modal，pill 步骤指示器
 */

import React, { useState } from "react";
import { Modal, App, Form, Button } from "antd";
import { CheckOutlined, ArrowRightOutlined } from "@ant-design/icons";
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
 * Step 2 表单区域
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
          message.success(t("createDialog.created"));
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
      {/* 步骤指示器 pills */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
        <span className="step-pill step-pill-completed">
          <CheckOutlined style={{ fontSize: 10 }} />
          {t("createDialog.steps.selectType")}
        </span>
        <ArrowRightOutlined style={{ color: "var(--mf-text-muted, #999)", fontSize: 12 }} />
        <span className="step-pill step-pill-active">
          {selectedTypeInfo?.title || t("createDialog.steps.configure")}
        </span>
      </div>
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
      title={t("createDialog.title")}
      open={open}
      onCancel={handleClose}
      width={520}
      footer={
        currentStep === 0
          ? null
          : [
              <Button
                key="back"
                onClick={() => setCurrentStep(0)}
                style={{ borderRadius: 8, padding: "8px 16px" }}
              >
                {t("common:actions.back")}
              </Button>,
              <Button
                key="submit"
                type="primary"
                onClick={handleSubmit}
                disabled={isSubmitting}
                style={{ borderRadius: 8, padding: "8px 20px" }}
              >
                {isSubmitting ? t("common:actions.creating") : t("createDialog.create")}
              </Button>,
            ]
      }
      destroyOnHidden
    >
      {/* Step 1: 副标题 */}
      {currentStep === 0 && (
        <p style={{ color: "var(--mf-text-secondary, #666)", fontSize: 13, marginBottom: 12 }}>
          {t("createDialog.subtitle")}
        </p>
      )}

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
