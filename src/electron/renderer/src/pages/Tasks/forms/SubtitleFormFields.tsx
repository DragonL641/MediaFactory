/**
 * 字幕生成表单字段（不含 Form 包装和文件输入）
 * 用于 CreateTaskDialog 和 EditTaskDialog 共享
 */

import React, { useState } from "react";
import { Form, Select, Switch } from "antd";
import type { FormInstance } from "antd";
import { useTranslation } from "react-i18next";
import {
  useLanguageOptions,
  useTargetLanguageOptions,
  useOutputFormatOptions,
  useStylePresetOptions,
  useBilingualLayoutOptions,
} from "./shared";
import LLMProviderSelect from "../../../components/Form/LLMProviderSelect";

interface SubtitleFormFieldsProps {
  form: FormInstance;
}

const SubtitleFormFields: React.FC<SubtitleFormFieldsProps> = ({ form }) => {
  const { t } = useTranslation("forms");
  const [useLlm, setUseLlm] = useState(false);
  const [bilingual, setBilingual] = useState(false);
  const outputFormat = Form.useWatch("output_format", form);

  const languageOptions = useLanguageOptions();
  const targetLanguageOptions = useTargetLanguageOptions();
  const outputFormatOptions = useOutputFormatOptions();
  const stylePresetOptions = useStylePresetOptions();
  const bilingualLayoutOptions = useBilingualLayoutOptions();

  const showAssPreset = outputFormat === "ass";
  const showBilingual = outputFormat === "srt" || outputFormat === "ass";

  return (
    <>
      <Form.Item name="source_lang" label={t("forms:label.sourceLanguage")}>
        <Select options={languageOptions} />
      </Form.Item>

      <Form.Item name="target_lang" label={t("forms:label.targetLanguage")}>
        <Select options={targetLanguageOptions} />
      </Form.Item>

      <Form.Item name="output_format" label={t("forms:label.outputFormat")}>
        <Select options={outputFormatOptions} />
      </Form.Item>

      {showAssPreset && (
        <Form.Item name="style_preset" label={t("forms:label.stylePreset")}>
          <Select options={stylePresetOptions} />
        </Form.Item>
      )}

      {showBilingual && (
        <>
          <Form.Item name="bilingual" label={t("forms:label.bilingualSubtitles")} valuePropName="checked">
            <Switch onChange={(checked) => setBilingual(checked)} />
          </Form.Item>

          {bilingual && (
            <Form.Item name="bilingual_layout" label={t("forms:label.layout")}>
              <Select options={bilingualLayoutOptions} />
            </Form.Item>
          )}
        </>
      )}

      <Form.Item name="use_llm" label={t("forms:label.useRemoteLlm")} valuePropName="checked">
        <Switch onChange={(checked) => setUseLlm(checked)} />
      </Form.Item>

      {useLlm && <LLMProviderSelect form={form} />}
    </>
  );
};

export default SubtitleFormFields;
