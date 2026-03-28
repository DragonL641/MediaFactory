/**
 * 编辑任务对话框
 *
 * 根据 task_type 显示对应的可编辑字段，
 * task_type 和 input_path 不可修改。
 */

import React, { useEffect, useState } from "react";
import { Modal, Form, Input, Select, Switch, InputNumber, Slider, App, Spin } from "antd";
import { isAxiosError } from "axios";
import { useTranslation } from "react-i18next";
import { useTaskConfigQuery, useUpdateTaskConfigMutation } from "../../api/queries";
import {
  useLanguageOptions,
  useTargetLanguageOptions,
  useOutputFormatOptions,
  useStylePresetOptions,
  useBilingualLayoutOptions,
} from "./forms/shared";

interface EditTaskDialogProps {
  taskId: string;
  open: boolean;
  onClose: () => void;
}

const TASK_TYPE_LABEL_KEYS: Record<string, string> = {
  subtitle: "tasks:typeLabels.subtitle",
  audio: "tasks:typeLabels.audio",
  transcribe: "tasks:typeLabels.transcribe",
  translate: "tasks:typeLabels.translate",
  enhance: "tasks:typeLabels.enhance",
};

const EditTaskDialog: React.FC<EditTaskDialogProps> = ({
  taskId,
  open,
  onClose,
}) => {
  const [form] = Form.useForm();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const { data: config, isLoading } = useTaskConfigQuery(taskId);
  const updateMutation = useUpdateTaskConfigMutation();

  // i18n 选项
  const languageOptions = useLanguageOptions();
  const targetLanguageOptions = useTargetLanguageOptions();
  const outputFormatOptions = useOutputFormatOptions();
  const stylePresetOptions = useStylePresetOptions();
  const bilingualLayoutOptions = useBilingualLayoutOptions();

  const [useLlm, setUseLlm] = useState(false);
  const [bilingual, setBilingual] = useState(false);
  const [filterEnabled, setFilterEnabled] = useState(true);
  const outputFormat = Form.useWatch("output_format", form);

  useEffect(() => {
    if (config && open) {
      form.setFieldsValue(config);
      setUseLlm(config.use_llm || false);
      setBilingual(config.bilingual || false);
      setFilterEnabled(config.audio_filter_enabled !== false);
    }
  }, [config, form, open]);

  useEffect(() => {
    if (!open) {
      form.resetFields();
      setUseLlm(false);
      setBilingual(false);
      setFilterEnabled(true);
    }
  }, [open, form]);

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      await updateMutation.mutateAsync({ taskId, config: values });
      message.success(t("tasks:messages.configUpdated"));
      onClose();
    } catch (error: unknown) {
      if (isAxiosError(error) && error.response?.data?.detail) {
        message.error(error.response.data.detail);
      }
    }
  };

  const renderEditFields = () => {
    if (!config) return null;
    const taskType = config.task_type as string;

    switch (taskType) {
      case "subtitle":
        return (
          <>
            <Form.Item name="source_lang" label={t("forms:label.sourceLanguage")}>
              <Select options={languageOptions} />
            </Form.Item>
            <Form.Item name="target_lang" label={t("forms:label.targetLanguage")}>
              <Select options={targetLanguageOptions} />
            </Form.Item>
            <Form.Item name="output_format" label={t("forms:label.outputFormat")}>
              <Select options={outputFormatOptions} />
            </Form.Item>
            {outputFormat === "ass" && (
              <Form.Item name="style_preset" label={t("forms:label.stylePreset")}>
                <Select options={stylePresetOptions} />
              </Form.Item>
            )}
            {(outputFormat === "srt" || outputFormat === "ass") && (
              <>
                <Form.Item name="bilingual" label={t("forms:label.bilingualSubtitles")} valuePropName="checked">
                  <Switch onChange={(checked) => setBilingual(checked)} />
                </Form.Item>
                {bilingual && (
                  <Form.Item name="bilingual_layout" label={t("forms:label.layout")}>
                    <Select options={bilingualLayoutOptions} />
                  </Form.Item>
                )}
              </>
            )}
            <Form.Item name="use_llm" label={t("forms:label.useRemoteLlm")} valuePropName="checked">
              <Switch onChange={(checked) => setUseLlm(checked)} />
            </Form.Item>
            {useLlm && (
              <Form.Item name="llm_preset" label={t("forms:label.llmProvider")}>
                <Input />
              </Form.Item>
            )}
          </>
        );

      case "audio":
        return (
          <>
            <Form.Item name="audio_output_format" label={t("forms:audioLabels.outputFormat")}>
              <Select
                options={[
                  { value: "wav", label: t("forms:audioOptions.wav") },
                  { value: "mp3", label: t("forms:audioOptions.mp3") },
                  { value: "flac", label: t("forms:audioOptions.flac") },
                  { value: "aac", label: t("forms:audioOptions.aac") },
                ]}
              />
            </Form.Item>
            <Form.Item name="audio_sample_rate" label={t("forms:audioLabels.sampleRate")}>
              <Select
                options={[
                  { value: 48000, label: t("forms:sampleRate.best") },
                  { value: 44100, label: t("forms:sampleRate.cd") },
                  { value: 22050, label: t("forms:sampleRate.standard") },
                  { value: 16000, label: t("forms:sampleRate.speech") },
                ]}
              />
            </Form.Item>
            <Form.Item name="audio_channels" label={t("forms:audioLabels.channels")}>
              <Select
                options={[
                  { value: 2, label: t("forms:channels.stereo") },
                  { value: 1, label: t("forms:channels.mono") },
                ]}
              />
            </Form.Item>
            <Form.Item name="audio_filter_enabled" label={t("forms:audioLabels.voiceEnhancementFilter")} valuePropName="checked">
              <Switch onChange={setFilterEnabled} />
            </Form.Item>
            {filterEnabled && (
              <>
                <Form.Item name="audio_highpass_freq" label={t("forms:audioLabels.highpass")}>
                  <InputNumber min={20} max={500} style={{ width: "100%" }} />
                </Form.Item>
                <Form.Item name="audio_lowpass_freq" label={t("forms:audioLabels.lowpass")}>
                  <InputNumber min={1000} max={16000} style={{ width: "100%" }} />
                </Form.Item>
                <Form.Item name="audio_volume" label={t("forms:audioLabels.volumeMultiplier")}>
                  <Slider min={0.1} max={2.0} step={0.1} />
                </Form.Item>
              </>
            )}
          </>
        );

      case "transcribe":
        return (
          <>
            <Form.Item name="source_lang" label={t("forms:label.sourceLanguage")}>
              <Select options={languageOptions} />
            </Form.Item>
            <Form.Item name="output_format" label={t("forms:label.outputFormat")}>
              <Select options={outputFormatOptions} />
            </Form.Item>
            {outputFormat === "ass" && (
              <Form.Item name="style_preset" label={t("forms:label.stylePreset")}>
                <Select options={stylePresetOptions} />
              </Form.Item>
            )}
          </>
        );

      case "translate":
        return (
          <>
            <Form.Item name="source_lang" label={t("forms:label.sourceLanguage")}>
              <Select options={languageOptions} />
            </Form.Item>
            <Form.Item name="target_lang" label={t("forms:label.targetLanguage")}>
              <Select options={targetLanguageOptions} />
            </Form.Item>
            <Form.Item name="use_llm" label={t("forms:label.useRemoteLlm")} valuePropName="checked">
              <Switch onChange={(checked) => setUseLlm(checked)} />
            </Form.Item>
            {useLlm && (
              <Form.Item name="llm_preset" label={t("forms:label.llmProvider")}>
                <Input />
              </Form.Item>
            )}
          </>
        );

      case "enhance":
        return (
          <>
            <Form.Item name="enhancement_scale" label={t("forms:enhanceLabels.scale")}>
              <Select
                options={[
                  { value: 2, label: "2x" },
                  { value: 4, label: "4x" },
                ]}
              />
            </Form.Item>
            <Form.Item name="enhancement_model" label={t("forms:enhanceLabels.modelType")}>
              <Select
                options={[
                  { value: "general", label: t("forms:enhanceLabels.general") },
                  { value: "anime", label: t("forms:enhanceLabels.anime") },
                ]}
              />
            </Form.Item>
            <Form.Item name="enhancement_denoise" label={t("forms:enhanceLabels.enableDenoising")} valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="enhancement_temporal" label={t("forms:enhanceLabels.enableTemporalSmoothing")} valuePropName="checked">
              <Switch />
            </Form.Item>
          </>
        );

      default:
        return null;
    }
  };

  return (
    <Modal
      title={t("tasks:editDialog.title")}
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
          <Form.Item label={t("tasks:editDialog.taskType")}>
            <Input value={t(TASK_TYPE_LABEL_KEYS[config?.task_type] || config?.task_type) || config?.task_type} disabled />
          </Form.Item>
          <Form.Item label={t("tasks:editDialog.inputFile")}>
            <Input value={config?.input_path} disabled />
          </Form.Item>
          {renderEditFields()}
        </Form>
      )}
    </Modal>
  );
};

export default EditTaskDialog;
