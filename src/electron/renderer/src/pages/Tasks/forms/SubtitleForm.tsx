/**
 * 字幕生成表单
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
  useFileFilters,
} from "./shared";
import FileDialogInput from "../../../components/Form/FileDialogInput";
import LLMProviderSelect from "../../../components/Form/LLMProviderSelect";

interface SubtitleFormProps {
  form: FormInstance;
}

const SubtitleForm: React.FC<SubtitleFormProps> = ({ form }) => {
  const { t } = useTranslation("forms");
  const [useLlm, setUseLlm] = useState(false);
  const [bilingual, setBilingual] = useState(false);
  const outputFormat = Form.useWatch(["output_format"], form);

  const languageOptions = useLanguageOptions();
  const targetLanguageOptions = useTargetLanguageOptions();
  const outputFormatOptions = useOutputFormatOptions();
  const stylePresetOptions = useStylePresetOptions();
  const bilingualLayoutOptions = useBilingualLayoutOptions();
  const fileFilters = useFileFilters();

  const showAssPreset = outputFormat === "ass";
  const showBilingual = outputFormat === "srt" || outputFormat === "ass";

  return (
    <Form form={form} layout="vertical" initialValues={{
      source_lang: "auto",
      target_lang: "zh",
      output_format: "srt",
      style_preset: "default",
      bilingual: false,
      bilingual_layout: "translate_on_top",
      use_llm: false,
    }}>
      <FileDialogInput
        form={form}
        name="video_path"
        label={t("forms:label.videoFile")}
        placeholder={t("forms:placeholder.selectVideo")}
        filters={fileFilters.video}
      />

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
    </Form>
  );
};

export default SubtitleForm;
