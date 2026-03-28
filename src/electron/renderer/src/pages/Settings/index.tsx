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
  App,
  Result,
} from "antd";
import { SaveOutlined, ReloadOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import {
  useConfigQuery,
  useUpdateConfigMutation,
  useSaveConfigMutation,
  useReloadConfigMutation,
} from "../../api/queries";
import PageHeader from "../../components/Layout/PageHeader";
import { PageSkeleton } from "../../components/common";
import { isAxiosError } from "axios";
import type { AppConfig } from "../../types";

const SettingsPage: React.FC = () => {
  const [form] = Form.useForm();
  const { message } = App.useApp();
  const { t } = useTranslation("settings");

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
        message.success(t("settings:messages.configUpdated"));
      },
      onError: (error: unknown) => {
        const detail = isAxiosError(error) ? error.response?.data?.detail : undefined;
        message.error(detail || t("settings:messages.updateFailed"));
      },
    });
  };

  if (isLoading) {
    return <PageSkeleton type="settings" />;
  }

  if (isError) {
    return (
      <div style={{ padding: 48 }}>
        <Result
          status="error"
          title={t("settings:error.loadFailed")}
          subTitle={t("common:error.connectFailed")}
          extra={
            <Button type="primary" onClick={() => refetch()}>
              {t("common:error.retry")}
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className="page-enter">
      <PageHeader
        title={t("settings:pageHeader.title")}
        description={t("settings:pageHeader.description")}
      />

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        style={{ maxWidth: 720 }}
      >
        {/* Whisper 设置 */}
        <Card
          title={
            <span style={{ fontSize: 15, fontWeight: 600 }}>
              {t("settings:whisper.title")}
            </span>
          }
          style={{ marginBottom: 24 }}
          styles={{ body: { paddingTop: 16 } }}
        >
          <div className="form-row">
            <Form.Item
              name={["whisper", "beam_size"]}
              label={t("settings:whisper.beamSize")}
              tooltip={t("settings:whisper.beamSizeTooltip")}
            >
              <InputNumber min={1} max={10} style={{ width: "100%" }} />
            </Form.Item>

            <Form.Item
              name={["whisper", "vad_threshold"]}
              label={t("settings:whisper.vadThreshold")}
              tooltip={t("settings:whisper.vadThresholdTooltip")}
            >
              <InputNumber min={0} max={1} step={0.05} style={{ width: "100%" }} />
            </Form.Item>
          </div>

          <div className="form-row">
            <Form.Item
              name={["whisper", "vad_filter"]}
              label={t("settings:whisper.vadFilter")}
              valuePropName="checked"
              tooltip={t("settings:whisper.vadFilterTooltip")}
            >
              <Switch />
            </Form.Item>

            <Form.Item
              name={["whisper", "word_timestamps"]}
              label={t("settings:whisper.wordTimestamps")}
              valuePropName="checked"
              tooltip={t("settings:whisper.wordTimestampsTooltip")}
            >
              <Switch />
            </Form.Item>
          </div>
        </Card>

        {/* 操作按钮 - 右对齐 */}
        <div className="form-actions">
          <Button
            icon={<ReloadOutlined />}
            onClick={() =>
              reloadConfigMutation.mutate(undefined, {
                onSuccess: (data: { config?: AppConfig }) => {
                  message.success(t("settings:messages.configReloaded"));
                  form.setFieldsValue({ whisper: data.config?.whisper });
                },
              })
            }
            loading={reloadConfigMutation.isPending}
          >
            {t("settings:actions.reload")}
          </Button>
          <Button
            icon={<SaveOutlined />}
            onClick={() =>
              saveConfigMutation.mutate(undefined, {
                onSuccess: () => message.success(t("settings:messages.savedToDisk")),
              })
            }
            loading={saveConfigMutation.isPending}
          >
            {t("settings:actions.saveToDisk")}
          </Button>
          <Button
            type="primary"
            htmlType="submit"
            icon={<SaveOutlined />}
            loading={updateConfigMutation.isPending}
          >
            {t("settings:actions.apply")}
          </Button>
        </div>
      </Form>
    </div>
  );
};

export default SettingsPage;
