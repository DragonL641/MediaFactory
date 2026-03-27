/**
 * 设置页面
 *
 * 全局配置：Whisper 转录高级设置
 * LLM 相关配置已迁移到 LLM Config 页面
 */

import React from "react";
import {
  Card,
  Form,
  InputNumber,
  Switch,
  Button,
  Space,
  App,
  Divider,
  Skeleton,
  Result,
} from "antd";
import { SaveOutlined, ReloadOutlined } from "@ant-design/icons";
import {
  useConfigQuery,
  useUpdateConfigMutation,
  useSaveConfigMutation,
  useReloadConfigMutation,
} from "../../api/queries";
import { isAxiosError } from "axios";
import type { AppConfig } from "../../types";
import PageHeader from "../../components/Layout/PageHeader";

const SettingsPage: React.FC = () => {
  const [form] = Form.useForm();
  const { message } = App.useApp();

  const { data: config, isLoading, isError, refetch } = useConfigQuery();

  const updateConfigMutation = useUpdateConfigMutation();
  const saveConfigMutation = useSaveConfigMutation();
  const reloadConfigMutation = useReloadConfigMutation();

  // 配置加载后设置表单值
  React.useEffect(() => {
    if (config) {
      form.setFieldsValue({
        whisper: config.whisper,
      });
    }
  }, [config, form]);

  // 提交表单
  const handleSubmit = (values: { whisper: AppConfig["whisper"] }) => {
    updateConfigMutation.mutate(values, {
      onSuccess: () => {
        message.success("Configuration updated");
      },
      onError: (error: unknown) => {
        const detail = isAxiosError(error) ? error.response?.data?.detail : undefined;
        message.error(detail || "Failed to update config");
      },
    });
  };

  if (isLoading) {
    return (
      <div className="page-enter">
        <PageHeader title="Settings" />
        <Card style={{ marginBottom: 16 }}><Skeleton active paragraph={{ rows: 4 }} /></Card>
      </div>
    );
  }

  if (isError) {
    return (
      <div style={{ padding: 48 }}>
        <Result
          status="error"
          title="Failed to load settings"
          subTitle="Unable to connect to the backend service"
          extra={
            <Button type="primary" onClick={() => refetch()}>
              Retry
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className="page-enter">
      <PageHeader title="Settings" />

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        style={{ maxWidth: 800 }}
      >
        {/* Whisper 设置 */}
        <Card title="Whisper Transcription" style={{ marginBottom: 16 }}>
          <Form.Item
            name={["whisper", "beam_size"]}
            label="Beam Size"
            tooltip="Higher values improve accuracy but slow down transcription"
          >
            <InputNumber min={1} max={10} style={{ width: "100%" }} />
          </Form.Item>

          <Form.Item
            name={["whisper", "vad_filter"]}
            label="VAD Filter"
            valuePropName="checked"
            tooltip="Voice Activity Detection - filters out silence"
          >
            <Switch />
          </Form.Item>

          <Form.Item
            name={["whisper", "vad_threshold"]}
            label="VAD Threshold"
            tooltip="Threshold for voice detection (0-1)"
          >
            <InputNumber min={0} max={1} step={0.05} style={{ width: "100%" }} />
          </Form.Item>

          <Form.Item
            name={["whisper", "word_timestamps"]}
            label="Word-level Timestamps"
            valuePropName="checked"
            tooltip="Generate timestamps for each word"
          >
            <Switch />
          </Form.Item>
        </Card>

        <Divider />

        {/* 操作按钮 */}
        <Form.Item>
          <Space>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SaveOutlined />}
              loading={updateConfigMutation.isPending}
            >
              Update
            </Button>
            <Button
              icon={<SaveOutlined />}
              onClick={() =>
                saveConfigMutation.mutate(undefined, {
                  onSuccess: () => message.success("Saved to disk"),
                })
              }
              loading={saveConfigMutation.isPending}
            >
              Save to Disk
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={() =>
                reloadConfigMutation.mutate(undefined, {
                  onSuccess: (data: { config?: AppConfig }) => {
                    message.success("Configuration reloaded");
                    form.setFieldsValue({ whisper: data.config?.whisper });
                  },
                })
              }
              loading={reloadConfigMutation.isPending}
            >
              Reload
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </div>
  );
};

export default SettingsPage;
