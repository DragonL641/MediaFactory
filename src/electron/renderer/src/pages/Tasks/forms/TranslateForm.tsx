/**
 * 字幕翻译表单
 */

import React, { useState } from "react";
import { Form, Select, Switch } from "antd";
import type { FormInstance } from "antd";
import { useTranslation } from "react-i18next";
import { useLanguageOptions, useTargetLanguageOptions, useFileFilters } from "./shared";
import FileDialogInput from "../../../components/Form/FileDialogInput";
import LLMProviderSelect from "../../../components/Form/LLMProviderSelect";

interface TranslateFormProps {
  form: FormInstance;
}

const TranslateForm: React.FC<TranslateFormProps> = ({ form }) => {
  const { t } = useTranslation("forms");
  const [useLlm, setUseLlm] = useState(false);

  const languageOptions = useLanguageOptions();
  const targetLanguageOptions = useTargetLanguageOptions();
  const fileFilters = useFileFilters();

  return (
    <Form form={form} layout="vertical" initialValues={{
      source_lang: "auto",
      target_lang: "zh",
      use_llm: false,
    }}>
      <FileDialogInput
        form={form}
        name="srt_path"
        label={t("forms:label.srtFile")}
        placeholder={t("forms:placeholder.selectSrt")}
        filters={fileFilters.srt}
      />

      <Form.Item name="source_lang" label={t("forms:label.sourceLanguage")}>
        <Select options={languageOptions} />
      </Form.Item>

      <Form.Item name="target_lang" label={t("forms:label.targetLanguage")}>
        <Select options={targetLanguageOptions} />
      </Form.Item>

      <Form.Item name="use_llm" label={t("forms:label.useRemoteLlmShort")} valuePropName="checked">
        <Switch onChange={(checked) => setUseLlm(checked)} />
      </Form.Item>

      {useLlm && <LLMProviderSelect form={form} />}
    </Form>
  );
};

export default TranslateForm;
