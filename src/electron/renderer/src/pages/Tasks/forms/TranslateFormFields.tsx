/**
 * 字幕翻译表单字段（不含 Form 包装和文件输入）
 */

import React, { useState } from "react";
import { Form, Select, Switch } from "antd";
import type { FormInstance } from "antd";
import { useTranslation } from "react-i18next";
import { useLanguageOptions, useTargetLanguageOptions } from "./shared";
import LLMProviderSelect from "../../../components/Form/LLMProviderSelect";

interface TranslateFormFieldsProps {
  form: FormInstance;
}

const TranslateFormFields: React.FC<TranslateFormFieldsProps> = ({ form }) => {
  const { t } = useTranslation("forms");
  const [useLlm, setUseLlm] = useState(false);

  const languageOptions = useLanguageOptions();
  const targetLanguageOptions = useTargetLanguageOptions();

  return (
    <>
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
    </>
  );
};

export default TranslateFormFields;
