/**
 * 字幕翻译表单字段（不含 Form 包装和文件输入）
 */

import React from "react";
import {Form, Select} from "antd";
import type {FormInstance} from "antd";
import {useTranslation} from "react-i18next";
import {useLanguageOptions, useTargetLanguageOptions} from "./shared";
import LLMProviderSelect from "../../../components/Form/LLMProviderSelect";
import LocalFallbackField from "./LocalFallbackField";
import TerminologyFileField from "./TerminologyFileField";

interface TranslateFormFieldsProps {
  form: FormInstance;
  llmAvailable?: boolean;
}

const TranslateFormFields: React.FC<TranslateFormFieldsProps> = ({form, llmAvailable = true}) => {
  const {t} = useTranslation("forms");

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

      {/* 翻译已强制 LLM-only（R1），不再提供关闭开关 */}
      {!llmAvailable && (
        <div style={{marginTop: -8, marginBottom: 12, fontSize: 12, color: "var(--mf-text-muted, #999)"}}>
          {t("forms:llm.configureInSettings")}
        </div>
      )}

      {llmAvailable && <LLMProviderSelect form={form} />}
      {llmAvailable && <LocalFallbackField form={form} />}

      <TerminologyFileField form={form} />
    </>
  );
};

export default TranslateFormFields;
