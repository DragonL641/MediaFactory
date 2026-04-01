/**
 * 音频提取表单
 */

import React from "react";
import type { FormInstance } from "antd";
import { useTranslation } from "react-i18next";
import { useFileFilters } from "./shared";
import TaskFormWrapper from "./TaskFormWrapper";
import AudioFormFields from "./AudioFormFields";

interface AudioFormProps {
  form: FormInstance;
}

const AudioForm: React.FC<AudioFormProps> = ({ form }) => {
  const { t } = useTranslation("forms");
  const fileFilters = useFileFilters();

  return (
    <TaskFormWrapper
      form={form}
      initialValues={{
        output_format: "wav",
        sample_rate: 48000,
        channels: 2,
        filter_enabled: true,
        highpass_freq: 200,
        lowpass_freq: 3000,
        volume: 1.0,
      }}
      fileInput={{
        name: "video_path",
        label: t("forms:label.videoFile"),
        placeholder: t("forms:placeholder.selectVideo"),
        filters: fileFilters.video,
      }}
    >
      <AudioFormFields />
    </TaskFormWrapper>
  );
};

export default AudioForm;
