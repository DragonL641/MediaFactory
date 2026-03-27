/**
 * 视频增强表单
 */

import React from "react";
import { Form, Select, Switch } from "antd";
import type { FormInstance } from "antd";
import FileDialogInput from "../../../components/Form/FileDialogInput";

interface EnhanceFormProps {
  form: FormInstance;
}

const EnhanceForm: React.FC<EnhanceFormProps> = ({ form }) => {
  return (
    <Form form={form} layout="vertical" initialValues={{
      scale: 4,
      model_type: "general",
      denoise: false,
      temporal: false,
    }}>
      <FileDialogInput
        form={form}
        name="video_path"
        label="Video File"
        placeholder="Click to select video file..."
        filters={[{ name: "Video Files", extensions: ["mp4", "avi", "mov", "mkv", "wmv", "flv", "webm"] }]}
      />

      <Form.Item name="scale" label="Scale">
        <Select
          options={[
            { value: 2, label: "2x" },
            { value: 4, label: "4x" },
          ]}
        />
      </Form.Item>

      <Form.Item name="model_type" label="Model Type">
        <Select
          options={[
            { value: "general", label: "General (Recommended)" },
            { value: "anime", label: "Anime" },
          ]}
        />
      </Form.Item>

      <Form.Item name="denoise" label="Enable Denoising" valuePropName="checked">
        <Switch />
      </Form.Item>

      <Form.Item name="temporal" label="Enable Temporal Smoothing" valuePropName="checked">
        <Switch />
      </Form.Item>
    </Form>
  );
};

export default EnhanceForm;
