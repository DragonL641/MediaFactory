/**
 * 语音转录表单字段（不含 Form 包装和文件输入）
 */

import React from "react";
import { Form, Select, Switch } from "antd";
import type { FormInstance } from "antd";
import { useTranslation } from "react-i18next";
import { useLanguageOptions, useOutputFormatOptions, useStylePresetOptions } from "./shared";

interface TranscribeFormFieldsProps {
  form: FormInstance;
}

const TranscribeFormFields: React.FC<TranscribeFormFieldsProps> = ({ form }) => {
  const { t } = useTranslation("forms");
  const outputFormat = Form.useWatch("output_format", form);

  const languageOptions = useLanguageOptions();
  const outputFormatOptions = useOutputFormatOptions();
  const stylePresetOptions = useStylePresetOptions();

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

      <Form.Item name="diarization_enabled" label={t("forms:label.speakerDiarization")} valuePropName="checked">
        <Switch />
      </Form.Item>
    </>
  );
};

export default TranscribeFormFields;
