/**
 * 语音转录表单
 */

import React from "react";
import { Form, Select } from "antd";
import type { FormInstance } from "antd";
import { LANGUAGE_OPTIONS, OUTPUT_FORMAT_OPTIONS, STYLE_PRESET_OPTIONS } from "./shared";
import FileDialogInput from "../../../components/Form/FileDialogInput";

interface TranscribeFormProps {
  form: FormInstance;
}

const TranscribeForm: React.FC<TranscribeFormProps> = ({ form }) => {
  const outputFormat = Form.useWatch(["output_format"], form);

  return (
    <Form form={form} layout="vertical" initialValues={{
      source_lang: "auto",
      output_format: "srt",
      style_preset: "default",
    }}>
      <FileDialogInput
        form={form}
        name="audio_path"
        label="Audio/Video File"
        placeholder="Click to select audio or video file..."
        filters={[{ name: "Audio/Video Files", extensions: ["mp4", "avi", "mov", "mkv", "wav", "mp3", "m4a", "flac", "webm", "ogg"] }]}
      />

      <Form.Item name="source_lang" label="Source Language">
        <Select options={LANGUAGE_OPTIONS} />
      </Form.Item>

      <Form.Item name="output_format" label="Output Format">
        <Select options={OUTPUT_FORMAT_OPTIONS} />
      </Form.Item>

      {outputFormat === "ass" && (
        <Form.Item name="style_preset" label="Style Preset">
          <Select options={STYLE_PRESET_OPTIONS} />
        </Form.Item>
      )}
    </Form>
  );
};

export default TranscribeForm;
