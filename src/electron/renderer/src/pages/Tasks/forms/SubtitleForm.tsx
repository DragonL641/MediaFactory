/**
 * 字幕生成表单
 */

import React, { useState } from "react";
import { Form, Select, Switch } from "antd";
import type { FormInstance } from "antd";
import {
  LANGUAGE_OPTIONS,
  TARGET_LANGUAGE_OPTIONS,
  OUTPUT_FORMAT_OPTIONS,
  STYLE_PRESET_OPTIONS,
  BILINGUAL_LAYOUT_OPTIONS,
} from "./shared";
import FileDialogInput from "../../../components/Form/FileDialogInput";
import LLMProviderSelect from "../../../components/Form/LLMProviderSelect";

interface SubtitleFormProps {
  form: FormInstance;
}

const SubtitleForm: React.FC<SubtitleFormProps> = ({ form }) => {
  const [useLlm, setUseLlm] = useState(false);
  const [bilingual, setBilingual] = useState(false);
  const outputFormat = Form.useWatch(["output_format"], form);

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
        label="Video File"
        placeholder="Click to select video file..."
        filters={[{ name: "Video Files", extensions: ["mp4", "avi", "mov", "mkv", "wmv", "flv", "webm"] }]}
      />

      <Form.Item name="source_lang" label="Source Language">
        <Select options={LANGUAGE_OPTIONS} />
      </Form.Item>

      <Form.Item name="target_lang" label="Target Language">
        <Select options={TARGET_LANGUAGE_OPTIONS} />
      </Form.Item>

      <Form.Item name="output_format" label="Output Format">
        <Select options={OUTPUT_FORMAT_OPTIONS} />
      </Form.Item>

      {showAssPreset && (
        <Form.Item name="style_preset" label="Style Preset">
          <Select options={STYLE_PRESET_OPTIONS} />
        </Form.Item>
      )}

      {showBilingual && (
        <>
          <Form.Item name="bilingual" label="Bilingual Subtitles" valuePropName="checked">
            <Switch onChange={(checked) => setBilingual(checked)} />
          </Form.Item>

          {bilingual && (
            <Form.Item name="bilingual_layout" label="Layout">
              <Select options={BILINGUAL_LAYOUT_OPTIONS} />
            </Form.Item>
          )}
        </>
      )}

      <Form.Item name="use_llm" label="Use Remote LLM for Translation" valuePropName="checked">
        <Switch onChange={(checked) => setUseLlm(checked)} />
      </Form.Item>

      {useLlm && <LLMProviderSelect form={form} />}
    </Form>
  );
};

export default SubtitleForm;
