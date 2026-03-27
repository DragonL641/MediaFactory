/**
 * 编辑任务对话框
 *
 * 根据 task_type 显示对应的可编辑字段，
 * task_type 和 input_path 不可修改。
 */

import React, { useEffect, useState } from "react";
import { Modal, Form, Input, Select, Switch, InputNumber, Slider, App, Spin } from "antd";
import { isAxiosError } from "axios";
import { useTaskConfigQuery, useUpdateTaskConfigMutation } from "../../api/queries";
import {
  LANGUAGE_OPTIONS,
  TARGET_LANGUAGE_OPTIONS,
  OUTPUT_FORMAT_OPTIONS,
  STYLE_PRESET_OPTIONS,
  BILINGUAL_LAYOUT_OPTIONS,
} from "./forms/shared";

interface EditTaskDialogProps {
  taskId: string;
  open: boolean;
  onClose: () => void;
}

const TASK_TYPE_LABELS: Record<string, string> = {
  subtitle: "Subtitle Generation",
  audio: "Audio Extraction",
  transcribe: "Transcription",
  translate: "Translation",
  enhance: "Video Enhancement",
};

const EditTaskDialog: React.FC<EditTaskDialogProps> = ({
  taskId,
  open,
  onClose,
}) => {
  const [form] = Form.useForm();
  const { message } = App.useApp();
  const { data: config, isLoading } = useTaskConfigQuery(taskId);
  const updateMutation = useUpdateTaskConfigMutation();

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
      message.success("Task config updated");
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
            <Form.Item name="source_lang" label="Source Language">
              <Select options={LANGUAGE_OPTIONS} />
            </Form.Item>
            <Form.Item name="target_lang" label="Target Language">
              <Select options={TARGET_LANGUAGE_OPTIONS} />
            </Form.Item>
            <Form.Item name="output_format" label="Output Format">
              <Select options={OUTPUT_FORMAT_OPTIONS} />
            </Form.Item>
            {outputFormat === "ass" && (
              <Form.Item name="style_preset" label="Style Preset">
                <Select options={STYLE_PRESET_OPTIONS} />
              </Form.Item>
            )}
            {(outputFormat === "srt" || outputFormat === "ass") && (
              <>
                <Form.Item name="bilingual" label="Bilingual Subtitles" valuePropName="checked">
                  <Switch onChange={(checked) => setBilingual(checked)} />
                </Form.Item>
                {bilingual && (
                  <Form.Item name="bilingual_layout" label="Layout">
                    <Select options={BILINGUAL_LAYOUT_OPTIONS} />
                  </Form.Item>
                )}
              </>
            )}
            <Form.Item name="use_llm" label="Use Remote LLM" valuePropName="checked">
              <Switch onChange={(checked) => setUseLlm(checked)} />
            </Form.Item>
            {useLlm && (
              <Form.Item name="llm_preset" label="LLM Provider">
                <Input />
              </Form.Item>
            )}
          </>
        );

      case "audio":
        return (
          <>
            <Form.Item name="audio_output_format" label="Output Format">
              <Select
                options={[
                  { value: "wav", label: "WAV (Best Quality)" },
                  { value: "mp3", label: "MP3 (Smaller Size)" },
                  { value: "flac", label: "FLAC (Lossless)" },
                  { value: "aac", label: "AAC (Compressed)" },
                ]}
              />
            </Form.Item>
            <Form.Item name="audio_sample_rate" label="Sample Rate">
              <Select
                options={[
                  { value: 48000, label: "48000 Hz (Best)" },
                  { value: 44100, label: "44100 Hz (CD Quality)" },
                  { value: 22050, label: "22050 Hz" },
                  { value: 16000, label: "16000 Hz (Speech)" },
                ]}
              />
            </Form.Item>
            <Form.Item name="audio_channels" label="Channels">
              <Select
                options={[
                  { value: 2, label: "Stereo (2ch)" },
                  { value: 1, label: "Mono (1ch)" },
                ]}
              />
            </Form.Item>
            <Form.Item name="audio_filter_enabled" label="Voice Enhancement Filter" valuePropName="checked">
              <Switch onChange={setFilterEnabled} />
            </Form.Item>
            {filterEnabled && (
              <>
                <Form.Item name="audio_highpass_freq" label="Highpass (Hz)">
                  <InputNumber min={20} max={500} style={{ width: "100%" }} />
                </Form.Item>
                <Form.Item name="audio_lowpass_freq" label="Lowpass (Hz)">
                  <InputNumber min={1000} max={16000} style={{ width: "100%" }} />
                </Form.Item>
                <Form.Item name="audio_volume" label="Volume Multiplier">
                  <Slider min={0.1} max={2.0} step={0.1} />
                </Form.Item>
              </>
            )}
          </>
        );

      case "transcribe":
        return (
          <>
            <Form.Item name="source_lang" label="Source Language">
              <Select options={LANGUAGE_OPTIONS} />
            </Form.Item>
            <Form.Item name="output_format" label="Output Format">
              <Select options={OUTPUT_FORMAT_OPTIONS} />
            </Form.Item>
            {outputFormat === "ass" && (
              <Form.Item name="style_preset" label="Style Preset">
                <Select options={STYLE_PRESET_OPTIONS} />
              </Form.Item>
            )}
          </>
        );

      case "translate":
        return (
          <>
            <Form.Item name="source_lang" label="Source Language">
              <Select options={LANGUAGE_OPTIONS} />
            </Form.Item>
            <Form.Item name="target_lang" label="Target Language">
              <Select options={TARGET_LANGUAGE_OPTIONS} />
            </Form.Item>
            <Form.Item name="use_llm" label="Use Remote LLM" valuePropName="checked">
              <Switch onChange={(checked) => setUseLlm(checked)} />
            </Form.Item>
            {useLlm && (
              <Form.Item name="llm_preset" label="LLM Provider">
                <Input />
              </Form.Item>
            )}
          </>
        );

      case "enhance":
        return (
          <>
            <Form.Item name="enhancement_scale" label="Scale">
              <Select
                options={[
                  { value: 2, label: "2x" },
                  { value: 4, label: "4x" },
                ]}
              />
            </Form.Item>
            <Form.Item name="enhancement_model" label="Model Type">
              <Select
                options={[
                  { value: "general", label: "General (Recommended)" },
                  { value: "anime", label: "Anime" },
                ]}
              />
            </Form.Item>
            <Form.Item name="enhancement_denoise" label="Enable Denoising" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="enhancement_temporal" label="Enable Temporal Smoothing" valuePropName="checked">
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
      title="Edit Task"
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
          <Form.Item label="Task Type">
            <Input value={TASK_TYPE_LABELS[config?.task_type] || config?.task_type} disabled />
          </Form.Item>
          <Form.Item label="Input File">
            <Input value={config?.input_path} disabled />
          </Form.Item>
          {renderEditFields()}
        </Form>
      )}
    </Modal>
  );
};

export default EditTaskDialog;
