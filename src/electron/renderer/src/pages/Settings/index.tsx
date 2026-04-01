/**
 * Settings 页面
 *
 * 统一配置中心，包含 5 个区块：
 * 1. Speech Recognition — Whisper 模型管理 + 参数
 * 2. Local Translation Models — 翻译模型管理
 * 3. Remote LLM Providers — LLM 供应商管理 + API 参数
 * 4. Video Enhancement — 超分辨率 + 降噪模型管理
 * 5. General — 下载源、下载超时、日志保留
 */

import React, { useMemo, useState } from "react";
import {
  Card,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  Button,
  Space,
  App,
  Popconfirm,
  Tooltip,
} from "antd";
import {
  SaveOutlined,
  ReloadOutlined,
  SoundOutlined,
  TranslationOutlined,
  CloudOutlined,
  EyeOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  WifiOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import {
  useConfigQuery,
  useUpdateConfigMutation,
  useReloadConfigMutation,
  useModelsStatusQuery,
  useDownloadModelMutation,
  useDeleteModelMutation,
  useLLMPresetsQuery,
  useTestLLMMutation,
  useTestAllLLMMutation,
  useDeleteLLMPresetMutation,
} from "../../api/queries";
import { wsClient, getErrorDetail } from "../../api/client";
import PageHeader from "../../components/Layout/PageHeader";
import { PageSkeleton, ErrorPage, StatusTag } from "../../components/common";
import SettingsModelCard from "./ModelCard";
import ProviderDialog from "./ProviderDialog";
import type { AppConfig, LLMPresetInfo, TestConnectionResponse } from "../../types";

const SettingsPage: React.FC = () => {
  const [form] = Form.useForm();
  const { message } = App.useApp();
  const { t } = useTranslation(["settings", "models", "llmConfig", "common"]);

  // 数据查询
  const { data: config, isLoading: configLoading, isError: configError, refetch: refetchConfig } = useConfigQuery();
  const { data: modelsStatus, isLoading: modelsLoading, isError: modelsError, refetch: refetchModels } = useModelsStatusQuery();
  const { data: presets, refetch: refetchPresets } = useLLMPresetsQuery();

  // Mutations
  const updateConfigMutation = useUpdateConfigMutation();
  const reloadConfigMutation = useReloadConfigMutation();
  const downloadMutation = useDownloadModelMutation();
  const deleteModelMutation = useDeleteModelMutation();
  const testMutation = useTestLLMMutation();
  const testAllMutation = useTestAllLLMMutation();
  const deletePresetMutation = useDeleteLLMPresetMutation();

  const queryClient = useQueryClient();

  // 模型下载状态
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [downloadProgress, setDownloadProgress] = useState<number>(0);
  const downloadingIdRef = React.useRef(downloadingId);
  downloadingIdRef.current = downloadingId;

  // LLM Dialog 状态
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingPresetId, setEditingPresetId] = useState<string | null>(null);

  // WebSocket 监听下载进度
  React.useEffect(() => {
    const unsub1 = wsClient.subscribe("progress", (rawData) => {
      const data = rawData as Record<string, unknown>;
      const progressData = data.data as Record<string, unknown>;
      if (progressData?.stage === "download" && downloadingIdRef.current) {
        setDownloadProgress(Math.round((progressData.progress as number) || 0));
      }
    });
    const unsub2 = wsClient.subscribe("task_complete", (rawData) => {
      const msg = rawData as Record<string, unknown>;
      const taskData = (msg.data || {}) as Record<string, unknown>;
      if (msg.task_id && downloadingIdRef.current) {
        setDownloadingId(null);
        setDownloadProgress(0);
        if (taskData.success) {
          message.success(t("models:messages.downloadCompleted"));
        } else {
          message.error((taskData.error as string) || t("models:messages.downloadFailed"));
        }
        queryClient.invalidateQueries({ queryKey: ["models", "status"] });
      }
    });
    return () => { unsub1(); unsub2(); };
  }, [queryClient]);

  // 配置加载后设置表单值
  React.useEffect(() => {
    if (config) {
      form.setFieldsValue({
        whisper: config.whisper,
        llm_api: config.llm_api,
        model: config.model,
        logging: config.logging,
      });
    }
  }, [config, form]);

  // 提交配置
  const handleSubmit = (values: { whisper: AppConfig["whisper"]; llm_api: AppConfig["llm_api"]; model: AppConfig["model"]; logging: AppConfig["logging"] }) => {
    updateConfigMutation.mutate(values, {
      onSuccess: () => message.success(t("settings:messages.configUpdated")),
      onError: (error: unknown) => message.error(getErrorDetail(error) || t("settings:messages.updateFailed")),
    });
  };

  // 模型操作
  const handleDownload = (modelId: string) => {
    setDownloadingId(modelId);
    setDownloadProgress(0);
    downloadMutation.mutate(modelId, {
      onSuccess: () => message.success(t("models:messages.downloadStarted", { modelId })),
      onError: (error: unknown) => {
        message.error(getErrorDetail(error) || t("models:messages.downloadFailed"));
        setDownloadingId(null);
        setDownloadProgress(0);
      },
    });
  };

  const handleDeleteModel = (modelId: string) => {
    deleteModelMutation.mutate(modelId, {
      onSuccess: () => {
        message.success(t("models:messages.modelDeleted", { modelId }));
        if (downloadingId === modelId) setDownloadingId(null);
      },
      onError: (error: unknown) => message.error(getErrorDetail(error) || t("models:messages.deleteFailed")),
    });
  };

  // LLM Provider 操作
  const configuredPresets = useMemo(() => {
    if (!presets) return [];
    return (Object.entries(presets) as [string, LLMPresetInfo][])
      .filter(([id, info]) => {
        if (id === "custom") return info.configured && info.base_url;
        return info.configured && info.has_api_key;
      })
      .map(([id, info]) => ({
        id,
        displayName: info.display_name,
        baseUrl: info.base_url,
        model: info.model || info.model_examples?.[0] || "",
        hasApiKey: info.has_api_key,
        connectionAvailable: info.connection_available,
      }));
  }, [presets]);

  const handleTest = (presetId: string, displayName: string) => {
    testMutation.mutate(presetId, {
      onSuccess: (data: TestConnectionResponse) => {
        if (data.success) {
          message.success(t("llmConfig:card.connectedMsg", { name: displayName, latency: data.latency_ms }));
        } else {
          message.error(`${displayName}: ${data.error || t("llmConfig:card.connectionFailed")}`);
        }
      },
      onError: (error: unknown) => {
        message.error(`${displayName}: ${getErrorDetail(error) || t("llmConfig:card.testFailed")}`);
      },
    });
  };

  const handleTestAll = () => {
    testAllMutation.mutate(undefined, {
      onSuccess: () => {
        message.success(t("llmConfig:messages.allTested"));
        refetchPresets();
      },
    });
  };

  const handleDeleteProvider = (presetId: string) => {
    deletePresetMutation.mutate(presetId);
  };

  // 模型数据
  const whisperModels = modelsStatus?.whisper?.models || [];
  const translationModels = modelsStatus?.translation?.models || [];
  const enhancementModels = modelsStatus?.enhancement?.models || [];
  const denoiseModels = modelsStatus?.denoise?.models || [];

  const isLoading = configLoading || modelsLoading;
  const isError = configError || modelsError;

  if (isLoading) return <PageSkeleton type="settings" />;
  if (isError) return <ErrorPage title={t("settings:error.loadFailed")} onRetry={() => { refetchConfig(); refetchModels(); }} />;

  return (
    <div className="page-enter">
      <PageHeader
        title={t("settings:pageHeader.title")}
        description={t("settings:pageHeader.description")}
      />

      <Form form={form} layout="vertical" onFinish={handleSubmit}>
        {/* 区块 1: Speech Recognition */}
        <div className="settings-section-card" style={{ marginBottom: 24 }}>
          <div className="section-title">
            <span className="section-title-icon"><SoundOutlined /></span>
            <span>{t("settings:sections.speechRecognition")}</span>
          </div>

          {/* Whisper 模型卡片 */}
          <div style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 16 }}>
            {whisperModels.map((m) => (
              <SettingsModelCard
                key={m.id}
                name={m.purpose || m.name}
                subtitle={m.vram
                  ? t("models:card.subtitleWithVram", { name: m.name, size: m.size, memory: m.memory, vram: m.vram })
                  : t("models:card.subtitle", { name: m.name, size: m.size, memory: m.memory })
                }
                downloaded={m.downloaded}
                complete={m.complete}
                isDownloading={downloadingId === m.id}
                downloadProgress={downloadProgress}
                onDownload={() => handleDownload(m.id)}
                onDelete={() => handleDeleteModel(m.id)}
              />
            ))}
          </div>

          {/* 参数 */}
          <div className="form-row">
            <Form.Item name={["whisper", "beam_size"]} label={t("settings:whisper.beamSize")} tooltip={t("settings:whisper.beamSizeTooltip")}>
              <InputNumber min={1} max={10} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name={["whisper", "vad_filter"]} label={t("settings:whisper.vadFilter")} valuePropName="checked" tooltip={t("settings:whisper.vadFilterTooltip")}>
              <Switch />
            </Form.Item>
          </div>
        </div>

        {/* 区块 2: Local Translation Models */}
        <div className="settings-section-card" style={{ marginBottom: 24 }}>
          <div className="section-title">
            <span className="section-title-icon"><TranslationOutlined /></span>
            <span>{t("settings:sections.localTranslation")}</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {translationModels.map((m) => (
              <SettingsModelCard
                key={m.id}
                name={m.purpose || m.name}
                subtitle={m.vram
                  ? t("models:card.subtitleWithVram", { name: m.name, size: m.size, memory: m.memory, vram: m.vram })
                  : t("models:card.subtitle", { name: m.name, size: m.size, memory: m.memory })
                }
                downloaded={m.downloaded}
                complete={m.complete}
                isDownloading={downloadingId === m.id}
                downloadProgress={downloadProgress}
                onDownload={() => handleDownload(m.id)}
                onDelete={() => handleDeleteModel(m.id)}
              />
            ))}
          </div>
        </div>

        {/* 区块 3: Remote LLM Providers */}
        <div className="settings-section-card" style={{ marginBottom: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <div className="section-title" style={{ marginBottom: 0 }}>
              <span className="section-title-icon"><CloudOutlined /></span>
              <span>{t("settings:sections.remoteLLM")}</span>
            </div>
            <Space size={8}>
              {configuredPresets.length > 0 && (
                <Button onClick={handleTestAll} loading={testAllMutation.isPending} size="small">
                  {t("llmConfig:actions.testAll")}
                </Button>
              )}
              <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditingPresetId(null); setDialogOpen(true); }} size="small">
                {t("llmConfig:actions.addProvider")}
              </Button>
            </Space>
          </div>

          {/* Provider 卡片列表 */}
          <div style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 16 }}>
            {configuredPresets.map((preset) => (
              <div key={preset.id} className="provider-card">
                <div className="provider-card-header">
                  <div className="provider-card-info">
                    <div className="provider-card-name">{preset.displayName}</div>
                    <div className="provider-card-url">{preset.baseUrl}</div>
                    {preset.model && <div className="provider-card-model">{t("llmConfig:card.model", { model: preset.model })}</div>}
                  </div>
                  <div className="provider-card-actions">
                    {preset.connectionAvailable !== undefined && (
                      <StatusTag
                        status={preset.connectionAvailable ? "success" : "default"}
                        text={preset.connectionAvailable ? t("llmConfig:card.connected") : t("llmConfig:card.notConnected")}
                      />
                    )}
                    <Tooltip title={t("llmConfig:card.testTooltip")}>
                      <Button type="text" size="small" icon={<WifiOutlined />} loading={testMutation.isPending} onClick={() => handleTest(preset.id, preset.displayName)} />
                    </Tooltip>
                    <Tooltip title={t("llmConfig:card.editTooltip")}>
                      <Button type="text" size="small" icon={<EditOutlined />} onClick={() => { setEditingPresetId(preset.id); setDialogOpen(true); }} />
                    </Tooltip>
                    <Popconfirm
                      title={t("llmConfig:confirm.deleteTitle")}
                      description={t("llmConfig:confirm.deleteDescription")}
                      onConfirm={() => handleDeleteProvider(preset.id)}
                      okText={t("common:actions.delete")}
                      cancelText={t("common:actions.cancel")}
                      okButtonProps={{ danger: true }}
                    >
                      <Tooltip title={t("llmConfig:card.deleteTooltip")}>
                        <Button type="text" size="small" danger icon={<DeleteOutlined />} />
                      </Tooltip>
                    </Popconfirm>
                  </div>
                </div>
              </div>
            ))}
            {configuredPresets.length === 0 && (
              <div style={{ textAlign: "center", padding: "24px 0", color: "#999" }}>
                {t("llmConfig:empty.description")}
              </div>
            )}
          </div>

          {/* LLM API 参数 */}
          <div className="form-row">
            <Form.Item name={["llm_api", "timeout"]} label={t("settings:llmApi.timeout")} tooltip={t("settings:llmApi.timeoutTooltip")}>
              <InputNumber min={1} max={300} style={{ width: "100%" }} addonAfter="s" />
            </Form.Item>
            <Form.Item name={["llm_api", "temperature"]} label={t("settings:llmApi.temperature")} tooltip={t("settings:llmApi.temperatureTooltip")}>
              <InputNumber min={0} max={2} step={0.1} style={{ width: "100%" }} />
            </Form.Item>
          </div>
        </div>

        {/* 区块 4: Video Enhancement */}
        <div className="settings-section-card" style={{ marginBottom: 24 }}>
          <div className="section-title">
            <span className="section-title-icon"><EyeOutlined /></span>
            <span>{t("settings:sections.videoEnhancement")}</span>
          </div>

          {/* Super Resolution */}
          <div className="sub-section-title">{t("settings:subSections.superResolution")}</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 16 }}>
            {enhancementModels.map((m) => (
              <SettingsModelCard
                key={m.id}
                name={m.purpose || m.name}
                subtitle={m.vram
                  ? t("models:card.subtitleWithVram", { name: m.name, size: m.size, memory: m.memory, vram: m.vram })
                  : t("models:card.subtitle", { name: m.name, size: m.size, memory: m.memory })
                }
                downloaded={m.downloaded}
                complete={m.complete}
                isDownloading={downloadingId === m.id}
                downloadProgress={downloadProgress}
                onDownload={() => handleDownload(m.id)}
                onDelete={() => handleDeleteModel(m.id)}
              />
            ))}
          </div>

          {/* Video Denoising */}
          <div className="sub-section-title">{t("settings:subSections.videoDenoising")}</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {denoiseModels.map((m) => (
              <SettingsModelCard
                key={m.id}
                name={m.purpose || m.name}
                subtitle={m.vram
                  ? t("models:card.subtitleWithVram", { name: m.name, size: m.size, memory: m.memory, vram: m.vram })
                  : t("models:card.subtitle", { name: m.name, size: m.size, memory: m.memory })
                }
                downloaded={m.downloaded}
                complete={m.complete}
                isDownloading={downloadingId === m.id}
                downloadProgress={downloadProgress}
                onDownload={() => handleDownload(m.id)}
                onDelete={() => handleDeleteModel(m.id)}
              />
            ))}
          </div>
        </div>

        {/* 区块 5: General */}
        <div className="settings-section-card" style={{ marginBottom: 24 }}>
          <div className="section-title">
            <span className="section-title-icon"><SettingOutlined /></span>
            <span>{t("settings:sections.general")}</span>
          </div>

          <div className="form-row">
            <Form.Item name={["model", "download_source"]} label={t("settings:model.downloadSource")} tooltip={t("settings:model.downloadSourceTooltip")}>
              <Select
                options={[
                  { label: "HuggingFace Mirror (China)", value: "https://hf-mirror.com" },
                  { label: "HuggingFace (Global)", value: "https://huggingface.co" },
                ]}
              />
            </Form.Item>
            <Form.Item name={["model", "download_timeout"]} label={t("settings:general.downloadTimeout")} tooltip={t("settings:general.downloadTimeoutTooltip")}>
              <InputNumber min={10} max={600} style={{ width: "100%" }} addonAfter="s" />
            </Form.Item>
          </div>

          <div className="form-row">
            <Form.Item name={["logging", "retention_days"]} label={t("settings:general.logRetention")} tooltip={t("settings:general.logRetentionTooltip")}>
              <InputNumber min={1} max={365} style={{ width: "100%" }} addonAfter={t("settings:general.days")} />
            </Form.Item>
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="form-actions">
          <Button
            icon={<ReloadOutlined />}
            onClick={() =>
              reloadConfigMutation.mutate(undefined, {
                onSuccess: (data: { config?: AppConfig }) => {
                  message.success(t("settings:messages.configReloaded"));
                  if (data.config) {
                    form.setFieldsValue({
                      whisper: data.config.whisper,
                      llm_api: data.config.llm_api,
                      model: data.config.model,
                      logging: data.config.logging,
                    });
                  }
                },
              })
            }
            loading={reloadConfigMutation.isPending}
          >
            {t("settings:actions.reload")}
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

      {/* LLM Provider Dialog */}
      <ProviderDialog
        open={dialogOpen}
        editingPresetId={editingPresetId}
        onClose={() => { setDialogOpen(false); setEditingPresetId(null); }}
        onSuccess={() => refetchPresets()}
      />
    </div>
  );
};

export default SettingsPage;
