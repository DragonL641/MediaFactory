/**
 * 音频提取表单字段（不含 Form 包装和文件输入）
 * fieldPrefix 用于区分创建（无前缀）和编辑（"audio_" 前缀）的字段名
 */

import React from "react";
import { Form, Select, Switch, InputNumber, Slider } from "antd";
import type { FormInstance } from "antd";
import { useTranslation } from "react-i18next";

interface AudioFormFieldsProps {
  form: FormInstance;
  fieldPrefix?: string;
}

const AudioFormFields: React.FC<AudioFormFieldsProps> = ({ form, fieldPrefix = "" }) => {
  const { t } = useTranslation("forms");
  const filterEnabled = Form.useWatch(`${fieldPrefix}filter_enabled`, form);

  return (
    <>
      <Form.Item name={`${fieldPrefix}output_format`} label={t("forms:audioLabels.outputFormat")}>
        <Select
          options={[
            { value: "wav", label: t("forms:audioOptions.wav") },
            { value: "mp3", label: t("forms:audioOptions.mp3") },
            { value: "flac", label: t("forms:audioOptions.flac") },
            { value: "aac", label: t("forms:audioOptions.aac") },
          ]}
        />
      </Form.Item>

      <Form.Item name={`${fieldPrefix}sample_rate`} label={t("forms:audioLabels.sampleRate")}>
        <Select
          options={[
            { value: 48000, label: t("forms:sampleRate.best") },
            { value: 44100, label: t("forms:sampleRate.cd") },
            { value: 22050, label: t("forms:sampleRate.standard") },
            { value: 16000, label: t("forms:sampleRate.speech") },
          ]}
        />
      </Form.Item>

      <Form.Item name={`${fieldPrefix}channels`} label={t("forms:audioLabels.channels")}>
        <Select
          options={[
            { value: 2, label: t("forms:channels.stereo") },
            { value: 1, label: t("forms:channels.mono") },
          ]}
        />
      </Form.Item>

      <Form.Item name={`${fieldPrefix}filter_enabled`} label={t("forms:audioLabels.voiceEnhancementFilter")} valuePropName="checked">
        <Switch />
      </Form.Item>

      {filterEnabled && (
        <>
          <Form.Item name={`${fieldPrefix}highpass_freq`} label={t("forms:audioLabels.highpass")}>
            <InputNumber min={20} max={500} style={{ width: "100%" }} />
          </Form.Item>

          <Form.Item name={`${fieldPrefix}lowpass_freq`} label={t("forms:audioLabels.lowpass")}>
            <InputNumber min={1000} max={16000} style={{ width: "100%" }} />
          </Form.Item>

          <Form.Item name={`${fieldPrefix}volume`} label={t("forms:audioLabels.volumeMultiplier")}>
            <Slider min={0.1} max={2.0} step={0.1} />
          </Form.Item>
        </>
      )}
    </>
  );
};

export default AudioFormFields;
