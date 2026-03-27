/**
 * 音频提取表单
 */

import React from "react";
import { Form, Select, Switch, InputNumber, Slider } from "antd";
import type { FormInstance } from "antd";
import FileDialogInput from "../../../components/Form/FileDialogInput";

interface AudioFormProps {
  form: FormInstance;
}

const AudioForm: React.FC<AudioFormProps> = ({ form }) => {
  const [filterEnabled, setFilterEnabled] = React.useState(true);

  return (
    <Form form={form} layout="vertical" initialValues={{
      output_format: "wav",
      sample_rate: 48000,
      channels: 2,
      filter_enabled: true,
      highpass_freq: 200,
      lowpass_freq: 3000,
      volume: 1.0,
    }}>
      <FileDialogInput
        form={form}
        name="video_path"
        label="Video File"
        placeholder="Click to select video file..."
        filters={[{ name: "Video Files", extensions: ["mp4", "avi", "mov", "mkv", "wmv", "flv", "webm"] }]}
      />

      <Form.Item name="output_format" label="Output Format">
        <Select
          options={[
            { value: "wav", label: "WAV (Best Quality)" },
            { value: "mp3", label: "MP3 (Smaller Size)" },
            { value: "flac", label: "FLAC (Lossless)" },
            { value: "aac", label: "AAC (Compressed)" },
          ]}
        />
      </Form.Item>

      <Form.Item name="sample_rate" label="Sample Rate">
        <Select
          options={[
            { value: 48000, label: "48000 Hz (Best)" },
            { value: 44100, label: "44100 Hz (CD Quality)" },
            { value: 22050, label: "22050 Hz" },
            { value: 16000, label: "16000 Hz (Speech)" },
          ]}
        />
      </Form.Item>

      <Form.Item name="channels" label="Channels">
        <Select
          options={[
            { value: 2, label: "Stereo (2ch)" },
            { value: 1, label: "Mono (1ch)" },
          ]}
        />
      </Form.Item>

      <Form.Item name="filter_enabled" label="Voice Enhancement Filter" valuePropName="checked">
        <Switch defaultChecked onChange={setFilterEnabled} />
      </Form.Item>

      {filterEnabled && (
        <>
          <Form.Item name="highpass_freq" label="Highpass (Hz)">
            <InputNumber min={20} max={500} style={{ width: "100%" }} />
          </Form.Item>

          <Form.Item name="lowpass_freq" label="Lowpass (Hz)">
            <InputNumber min={1000} max={16000} style={{ width: "100%" }} />
          </Form.Item>

          <Form.Item name="volume" label="Volume Multiplier">
            <Slider min={0.1} max={2.0} step={0.1} />
          </Form.Item>
        </>
      )}
    </Form>
  );
};

export default AudioForm;
