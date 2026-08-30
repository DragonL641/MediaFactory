/**
 * 语音转录表单
 */

import React from "react";
import type { FormInstance } from "antd";
import { useTranslation } from "react-i18next";
import { useFileExtensions } from "./shared";
import TaskFormWrapper from "./TaskFormWrapper";
import TranscribeFormFields from "./TranscribeFormFields";

interface TranscribeFormProps {
  form: FormInstance;
}

const TranscribeForm: React.FC<TranscribeFormProps> = ({ form }) => {
  const { t } = useTranslation("forms");
  const fileExtensions = useFileExtensions();

  return (
    <TaskFormWrapper
      form={form}
      initialValues={{
        source_lang: "auto",
        output_format: "srt",
        style_preset: "default",
      }}
      fileInput={{
        name: "audio_path",
        label: t("forms:label.audioVideoFile"),
        placeholder: t("forms:placeholder.selectAudioVideo"),
        extensions: fileExtensions.audio_video,
      }}
    >
      <TranscribeFormFields form={form} />
    </TaskFormWrapper>
  );
};

export default TranscribeForm;
