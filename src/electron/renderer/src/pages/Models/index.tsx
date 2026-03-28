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
import { useTranslation } from "react-i18next";
import {
  useModelsStatusQuery,
  useDownloadModelMutation,
  useDeleteModelMutation,
} from "../../api/queries";
import { wsClient } from "../../api/client";
import PageHeader from "../../components/Layout/PageHeader";
import { StatusTag, PageSkeleton } from "../../components/common";
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
  const { t } = useTranslation("models");

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
                  {model.size && <div>{t("models:card.size", { size: model.size })}</div>}
                  {model.memory && <div>{t("models:card.memory", { memory: model.memory })}</div>}
                  {model.description && (
                    <div style={{ marginTop: 4, color: "#9CA3AF" }}>
                      {model.description}
                    </div>
                  )}
                </div>
                <div className="model-card-footer">
                  {isDownloading ? (
                    <StatusTag status="processing" text={t("models:card.downloading")} />
                  ) : isReady ? (
                    <>
                      <StatusTag status="success" text={t("models:card.ready")} />
                      <div style={{ flex: 1 }} />
                      <Popconfirm
                        title={t("models:confirm.deleteTitle")}
                        description={t("models:confirm.deleteDescription", { name: model.name })}
                        onConfirm={() => onDelete(model.id)}
                        okText={t("common:actions.delete")}
                        cancelText={t("common:actions.cancel")}
                        okButtonProps={{ danger: true }}
                      >
                        <Button size="small" type="text" danger icon={<DeleteOutlined />} />
                      </Popconfirm>
                    </>
                  ) : isIncomplete ? (
                    <>
                      <Tooltip title={t("models:card.incompleteTooltip")}>
                        <StatusTag status="warning" text={t("models:card.incomplete")} />
                      </Tooltip>
                      <div style={{ flex: 1 }} />
                      <Button
                        size="small"
                        type="link"
                        icon={<RedoOutlined />}
                        onClick={() => onDownload(model.id)}
                      >
                        {t("models:card.retry")}
                      </Button>
                      <Popconfirm
                        title={t("models:confirm.deleteTitle")}
                        description={t("models:confirm.deleteDescription", { name: model.name })}
                        onConfirm={() => onDelete(model.id)}
                        okText={t("common:actions.delete")}
                        cancelText={t("common:actions.cancel")}
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
                      {t("models:card.download")}
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
  const { t } = useTranslation("models");

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
          message.success(t("models:messages.downloadCompleted"));
        } else {
          message.error((data.error as string) || t("models:messages.downloadFailed"));
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
        message.success(t("models:messages.downloadStarted", { modelId }));
      },
      onError: (error: unknown) => {
        const detail = isAxiosError(error) ? error.response?.data?.detail : undefined;
        message.error(detail || t("models:messages.downloadFailed"));
        setDownloadingId(null);
      },
    });
  };

  const handleDelete = (modelId: string) => {
    deleteMutation.mutate(modelId, {
      onSuccess: () => {
        message.success(t("models:messages.modelDeleted", { modelId }));
        if (downloadingId === modelId) {
          setDownloadingId(null);
        }
      },
      onError: (error: unknown) => {
        const detail = isAxiosError(error) ? error.response?.data?.detail : undefined;
        message.error(detail || t("models:messages.deleteFailed"));
      },
    });
  };

  if (isLoading || !status) {
    return <PageSkeleton type="models" />;
  }

  if (isError) {
    return (
      <div style={{ padding: 48 }}>
        <Result
          status="error"
          title={t("models:error.loadFailed")}
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

  const whisperModels: ModelCardData[] = status.whisper?.models || [];
  const translationModels: ModelCardData[] = status.translation?.models || [];
  const enhancementModels: ModelCardData[] = status.enhancement?.models || [];
  const denoiseModels: ModelCardData[] = status.denoise?.models || [];

  return (
    <div className="page-enter">
      <PageHeader
        title={t("models:pageHeader.title")}
        description={t("models:pageHeader.description")}
        actions={
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
            {t("common:actions.refresh")}
          </Button>
        }
      />

      {/* Whisper */}
      <ModelCategory
        title={t("models:category.whisper.title")}
        description={t("models:category.whisper.description")}
        icon={<SoundOutlined />}
        models={whisperModels}
        onDownload={handleDownload}
        onDelete={handleDelete}
        downloadingId={downloadingId}
      />

      {/* Translation Models */}
      <ModelCategory
        title={t("models:category.translation.title")}
        description={t("models:category.translation.description")}
        icon={<TranslationOutlined />}
        models={translationModels}
        onDownload={handleDownload}
        onDelete={handleDelete}
        downloadingId={downloadingId}
      />

      {/* Super Resolution */}
      <ModelCategory
        title={t("models:category.enhancement.title")}
        description={t("models:category.enhancement.description")}
        icon={<ZoomInOutlined />}
        models={enhancementModels}
        onDownload={handleDownload}
        onDelete={handleDelete}
        downloadingId={downloadingId}
      />

      {/* Denoising */}
      <ModelCategory
        title={t("models:category.denoise.title")}
        description={t("models:category.denoise.description")}
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
