/**
 * 语音转录表单
 */

import React from "react";
import { Form, Select } from "antd";
import type { FormInstance } from "antd";
import { useTranslation } from "react-i18next";
import { useLanguageOptions, useOutputFormatOptions, useStylePresetOptions, useFileFilters } from "./shared";
import FileDialogInput from "../../../components/Form/FileDialogInput";

interface TranscribeFormProps {
  form: FormInstance;
}

const TranscribeForm: React.FC<TranscribeFormProps> = ({ form }) => {
  const { t } = useTranslation("forms");
  const outputFormat = Form.useWatch(["output_format"], form);

  const languageOptions = useLanguageOptions();
  const outputFormatOptions = useOutputFormatOptions();
  const stylePresetOptions = useStylePresetOptions();
  const fileFilters = useFileFilters();

  return (
    <Form form={form} layout="vertical" initialValues={{
      source_lang: "auto",
      output_format: "srt",
      style_preset: "default",
    }}>
      <FileDialogInput
        form={form}
        name="audio_path"
        label={t("forms:label.audioVideoFile")}
        placeholder={t("forms:placeholder.selectAudioVideo")}
        filters={fileFilters.audio_video}
      />

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
    </Form>
  );
};

export default TranscribeForm;
