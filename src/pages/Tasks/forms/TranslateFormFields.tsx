/**
 * 字幕翻译表单字段（不含 Form 包装和文件输入）
 */

import React from "react";
import { Form, Select, Switch } from "antd";
import type { FormInstance } from "antd";
import { useTranslation } from "react-i18next";
import { useLanguageOptions, useTargetLanguageOptions } from "./shared";
import LLMProviderSelect from "../../../components/Form/LLMProviderSelect";

interface TranslateFormFieldsProps {
  form: FormInstance;
  llmAvailable?: boolean;
}

const TranslateFormFields: React.FC<TranslateFormFieldsProps> = ({ form, llmAvailable = true }) => {
  const { t } = useTranslation("forms");
  const useLlm = Form.useWatch("use_llm", form);

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
        <Switch disabled={!llmAvailable} />
      </Form.Item>

      {!llmAvailable && (
        <div style={{ marginTop: -8, marginBottom: 12, fontSize: 12, color: "var(--mf-text-muted, #999)" }}>
          {t("forms:llm.configureInSettings")}
        </div>
      )}

      {useLlm && llmAvailable && <LLMProviderSelect form={form} />}
    </>
  );
};

export default TranslateFormFields;
