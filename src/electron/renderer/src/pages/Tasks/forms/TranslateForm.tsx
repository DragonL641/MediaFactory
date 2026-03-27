/**
 * 字幕翻译表单
 */

import React, { useState } from "react";
import { Form, Select, Switch } from "antd";
import type { FormInstance } from "antd";
import { LANGUAGE_OPTIONS, TARGET_LANGUAGE_OPTIONS } from "./shared";
import FileDialogInput from "../../../components/Form/FileDialogInput";
import LLMProviderSelect from "../../../components/Form/LLMProviderSelect";

interface TranslateFormProps {
  form: FormInstance;
}

const TranslateForm: React.FC<TranslateFormProps> = ({ form }) => {
  const [useLlm, setUseLlm] = useState(false);

  return (
    <Form form={form} layout="vertical" initialValues={{
      source_lang: "auto",
      target_lang: "zh",
      use_llm: false,
    }}>
      <FileDialogInput
        form={form}
        name="srt_path"
        label="SRT File"
        placeholder="Click to select SRT file..."
        filters={[{ name: "SRT Files", extensions: ["srt"] }]}
      />

      <Form.Item name="source_lang" label="Source Language">
        <Select options={LANGUAGE_OPTIONS} />
      </Form.Item>

      <Form.Item name="target_lang" label="Target Language">
        <Select options={TARGET_LANGUAGE_OPTIONS} />
      </Form.Item>

      <Form.Item name="use_llm" label="Use Remote LLM" valuePropName="checked">
        <Switch onChange={(checked) => setUseLlm(checked)} />
      </Form.Item>

      {useLlm && <LLMProviderSelect form={form} />}
    </Form>
  );
};

export default TranslateForm;
