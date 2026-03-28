/**
 * 音频提取表单
 */

import React from "react";
import { Form, Select, Switch, InputNumber, Slider } from "antd";
import type { FormInstance } from "antd";
import { useTranslation } from "react-i18next";
import { useFileFilters } from "./shared";
import FileDialogInput from "../../../components/Form/FileDialogInput";

interface AudioFormProps {
  form: FormInstance;
}

const AudioForm: React.FC<AudioFormProps> = ({ form }) => {
  const { t } = useTranslation("forms");
  const [filterEnabled, setFilterEnabled] = React.useState(true);
  const fileFilters = useFileFilters();

  return (
    <Form form={form} layout="vertical" initialValues={{
      output_format: "wav",
      sample_rate: 48000,
      channels: 2,
      filter_enabled: true,
      highpass_freq: 200,
      lowpass_freq: 3000,
      volume: 1.0,
    }}>
      <FileDialogInput
        form={form}
        name="video_path"
        label={t("forms:label.videoFile")}
        placeholder={t("forms:placeholder.selectVideo")}
        filters={fileFilters.video}
      />

      <Form.Item name="output_format" label={t("forms:audioLabels.outputFormat")}>
        <Select
          options={[
            { value: "wav", label: t("forms:audioOptions.wav") },
            { value: "mp3", label: t("forms:audioOptions.mp3") },
            { value: "flac", label: t("forms:audioOptions.flac") },
            { value: "aac", label: t("forms:audioOptions.aac") },
          ]}
        />
      </Form.Item>

      <Form.Item name="sample_rate" label={t("forms:audioLabels.sampleRate")}>
        <Select
          options={[
            { value: 48000, label: t("forms:sampleRate.best") },
            { value: 44100, label: t("forms:sampleRate.cd") },
            { value: 22050, label: t("forms:sampleRate.standard") },
            { value: 16000, label: t("forms:sampleRate.speech") },
          ]}
        />
      </Form.Item>

      <Form.Item name="channels" label={t("forms:audioLabels.channels")}>
        <Select
          options={[
            { value: 2, label: t("forms:channels.stereo") },
            { value: 1, label: t("forms:channels.mono") },
          ]}
        />
      </Form.Item>

      <Form.Item name="filter_enabled" label={t("forms:audioLabels.voiceEnhancementFilter")} valuePropName="checked">
        <Switch defaultChecked onChange={setFilterEnabled} />
      </Form.Item>

      {filterEnabled && (
        <>
          <Form.Item name="highpass_freq" label={t("forms:audioLabels.highpass")}>
            <InputNumber min={20} max={500} style={{ width: "100%" }} />
          </Form.Item>

          <Form.Item name="lowpass_freq" label={t("forms:audioLabels.lowpass")}>
            <InputNumber min={1000} max={16000} style={{ width: "100%" }} />
          </Form.Item>

          <Form.Item name="volume" label={t("forms:audioLabels.volumeMultiplier")}>
            <Slider min={0.1} max={2.0} step={0.1} />
          </Form.Item>
        </>
      )}
    </Form>
  );
};

export default AudioForm;
