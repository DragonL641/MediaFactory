/**
 * Models 页面
 *
 * 本地模型管理：Whisper、翻译模型、Real-ESRGAN、NAFNet
 * 对标 Flet 的 models.py
 */

import React from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  Typography,
  Row,
  Col,
  Card,
  Button,
  Popconfirm,
  App,
  Skeleton,
  Tooltip,
  Result,
} from "antd";
import {
  DownloadOutlined,
  DeleteOutlined,
  ReloadOutlined,
  SoundOutlined,
  TranslationOutlined,
  ZoomInOutlined,
  EyeOutlined,
  RedoOutlined,
} from "@ant-design/icons";
import {
  useModelsStatusQuery,
  useDownloadModelMutation,
  useDeleteModelMutation,
} from "../../api/queries";
import { wsClient } from "../../api/client";
import PageHeader from "../../components/Layout/PageHeader";
import { StatusTag } from "../../components/common";
import { isAxiosError } from "axios";

const { Text } = Typography;

interface ModelCardData {
  id: string;
  name: string;
  size?: string;
  memory?: string;
  description?: string;
  downloaded: boolean;
  complete?: boolean;
}

interface ModelCategoryProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  models: ModelCardData[];
  onDownload: (modelId: string) => void;
  onDelete: (modelId: string) => void;
  downloadingId?: string | null;
}

const ModelCategory: React.FC<ModelCategoryProps> = ({
  title,
  description,
  icon,
  models,
  onDownload,
  onDelete,
  downloadingId,
}) => {
  if (models.length === 0) {
    return null;
  }

  return (
    <div style={{ marginBottom: 28 }}>
      {/* 分类标题 */}
      <div className="section-title">
        <span className="section-title-icon">{icon}</span>
        <span>{title}</span>
      </div>
      <Text
        type="secondary"
        style={{ display: "block", marginBottom: 16, marginLeft: 38 }}
      >
        {description}
      </Text>

      <Row gutter={[16, 16]}>
        {models.map((model) => {
          const isDownloading = downloadingId === model.id;
          const isReady = model.downloaded && model.complete !== false;
          const isIncomplete = model.downloaded && model.complete === false;

          return (
            <Col xs={24} sm={12} lg={8} key={model.id}>
              <Card size="small" className="model-card" style={{ height: "100%" }}>
                <div className="model-card-header">
                  <span className="model-card-name">{model.name}</span>
                </div>
                <div className="model-card-meta">
                  {model.size && <div>Size: {model.size}</div>}
                  {model.memory && <div>Memory: {model.memory}</div>}
                  {model.description && (
                    <div style={{ marginTop: 4, color: "#9CA3AF" }}>
                      {model.description}
                    </div>
                  )}
                </div>
                <div className="model-card-footer">
                  {isDownloading ? (
                    <StatusTag status="processing" text="Downloading..." />
                  ) : isReady ? (
                    <>
                      <StatusTag status="success" text="Ready" />
                      <div style={{ flex: 1 }} />
                      <Popconfirm
                        title="Delete Model"
                        description={`Delete ${model.name}? This cannot be undone.`}
                        onConfirm={() => onDelete(model.id)}
                        okText="Delete"
                        cancelText="Cancel"
                        okButtonProps={{ danger: true }}
                      >
                        <Button size="small" type="text" danger icon={<DeleteOutlined />} />
                      </Popconfirm>
                    </>
                  ) : isIncomplete ? (
                    <>
                      <Tooltip title="Model files are incomplete or corrupted">
                        <StatusTag status="warning" text="Incomplete" />
                      </Tooltip>
                      <div style={{ flex: 1 }} />
                      <Button
                        size="small"
                        type="link"
                        icon={<RedoOutlined />}
                        onClick={() => onDownload(model.id)}
                      >
                        Retry
                      </Button>
                      <Popconfirm
                        title="Delete Model"
                        description={`Delete ${model.name}? This cannot be undone.`}
                        onConfirm={() => onDelete(model.id)}
                        okText="Delete"
                        cancelText="Cancel"
                        okButtonProps={{ danger: true }}
                      >
                        <Button size="small" type="text" danger icon={<DeleteOutlined />} />
                      </Popconfirm>
                    </>
                  ) : (
                    <Button
                      size="small"
                      type="primary"
                      icon={<DownloadOutlined />}
                      onClick={() => onDownload(model.id)}
                    >
                      Download
                    </Button>
                  )}
                </div>
              </Card>
            </Col>
          );
        })}
      </Row>
    </div>
  );
};

const ModelsPage: React.FC = () => {
  const { data: status, isLoading, isError, refetch } = useModelsStatusQuery();
  const downloadMutation = useDownloadModelMutation();
  const deleteMutation = useDeleteModelMutation();
  const { message } = App.useApp();

  // 当前正在下载的模型 ID
  const [downloadingId, setDownloadingId] = React.useState<string | null>(null);
  const queryClient = useQueryClient();

  // 监听 WebSocket task_complete 事件，清除下载状态并刷新模型列表
  React.useEffect(() => {
    const unsubscribe = wsClient.subscribe("task_complete", (rawData) => {
      const data = rawData as Record<string, unknown>;
      if (data.task_id && downloadingId) {
        setDownloadingId(null);
        if (data.success) {
          message.success("Download completed");
        } else {
          message.error((data.error as string) || "Download failed");
        }
        queryClient.invalidateQueries({ queryKey: ["models", "status"] });
      }
    });
    return unsubscribe;
  }, [downloadingId, queryClient]);

  const handleDownload = (modelId: string) => {
    setDownloadingId(modelId);
    downloadMutation.mutate(modelId, {
      onSuccess: () => {
        message.success(`Download started: ${modelId}`);
      },
      onError: (error: unknown) => {
        const detail = isAxiosError(error) ? error.response?.data?.detail : undefined;
        message.error(detail || "Download failed");
        setDownloadingId(null);
      },
    });
  };

  const handleDelete = (modelId: string) => {
    deleteMutation.mutate(modelId, {
      onSuccess: () => {
        message.success(`Model deleted: ${modelId}`);
        if (downloadingId === modelId) {
          setDownloadingId(null);
        }
      },
      onError: (error: unknown) => {
        const detail = isAxiosError(error) ? error.response?.data?.detail : undefined;
        message.error(detail || "Delete failed");
      },
    });
  };

  if (isLoading || !status) {
    return (
      <div className="page-enter">
        <PageHeader title="Local Models" actions={<Button icon={<ReloadOutlined />} />} />
        <Card style={{ marginBottom: 24 }}><Skeleton active paragraph={{ rows: 2 }} /></Card>
        <Card style={{ marginBottom: 24 }}><Skeleton active paragraph={{ rows: 3 }} /></Card>
      </div>
    );
  }

  if (isError) {
    return (
      <div style={{ padding: 48 }}>
        <Result
          status="error"
          title="Failed to load models"
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

  const whisperModels: ModelCardData[] = status.whisper?.models || [];
  const translationModels: ModelCardData[] = status.translation?.models || [];
  const enhancementModels: ModelCardData[] = status.enhancement?.models || [];
  const denoiseModels: ModelCardData[] = status.denoise?.models || [];

  return (
    <div className="page-enter">
      <PageHeader
        title="Local Models"
        description="Manage AI models for offline processing"
        actions={
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
            Refresh
          </Button>
        }
      />

      {/* Whisper */}
      <ModelCategory
        title="Audio Processing (Whisper)"
        description="Whisper models for speech recognition and transcription."
        icon={<SoundOutlined />}
        models={whisperModels}
        onDownload={handleDownload}
        onDelete={handleDelete}
        downloadingId={downloadingId}
      />

      {/* Translation Models */}
      <ModelCategory
        title="Translation (MADLAD400)"
        description="MADLAD400 models for local text translation."
        icon={<TranslationOutlined />}
        models={translationModels}
        onDownload={handleDownload}
        onDelete={handleDelete}
        downloadingId={downloadingId}
      />

      {/* Super Resolution */}
      <ModelCategory
        title="Super Resolution (Real-ESRGAN)"
        description="AI-powered video upscaling models."
        icon={<ZoomInOutlined />}
        models={enhancementModels}
        onDownload={handleDownload}
        onDelete={handleDelete}
        downloadingId={downloadingId}
      />

      {/* Denoising */}
      <ModelCategory
        title="Denoising (NAFNet)"
        description="Video denoise models for old or noisy footage."
        icon={<EyeOutlined />}
        models={denoiseModels}
        onDownload={handleDownload}
        onDelete={handleDelete}
        downloadingId={downloadingId}
      />
    </div>
  );
};

export default ModelsPage;
