/**
 * 任务卡片组件
 */

import React from "react";
import { Card, Progress, Tag, Button, Space, Typography, Tooltip, App } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  LoadingOutlined,
  PauseCircleOutlined,
  FolderOpenOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  EditOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { Task } from "../../types";
import { useStartTaskMutation } from "../../api/queries";
import { isAxiosError } from "axios";

const { Text } = Typography;

interface TaskCardProps {
  task: Task;
  onCancel: () => void;
  onDelete: () => void;
  onEdit?: () => void;
}

const TaskCard: React.FC<TaskCardProps> = ({ task, onCancel, onDelete, onEdit }) => {
  const status = task.status as string;
  const startMutation = useStartTaskMutation();
  const { message } = App.useApp();
  const { t } = useTranslation("tasks");

  const statusConfig: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
    pending: { color: "blue", icon: <ClockCircleOutlined />, text: t("tasks:card.status.pending") },
    running: { color: "processing", icon: <LoadingOutlined spin />, text: t("tasks:card.status.running") },
    completed: { color: "success", icon: <CheckCircleOutlined />, text: t("tasks:card.status.completed") },
    failed: { color: "error", icon: <CloseCircleOutlined />, text: t("tasks:card.status.failed") },
    cancelled: { color: "warning", icon: <PauseCircleOutlined />, text: t("tasks:card.status.cancelled") },
  };

  const config = statusConfig[status] || statusConfig.pending;

  const handleOpenLocation = async () => {
    const outputPath = task.outputPath;
    if (outputPath && window.electronAPI) {
      await window.electronAPI.openFileLocation(outputPath);
    }
  };

  const handleStart = () => {
    startMutation.mutate(task.id, {
      onSuccess: () => {
        message.success(t("tasks:card.started"));
      },
      onError: (error: unknown) => {
        const detail = isAxiosError(error) ? error.response?.data?.detail : undefined;
        message.error(detail || t("tasks:card.startFailed"));
      },
    });
  };

  const outputPath = task.outputPath;
  const isCompleted = status === "completed";
  const canStart = status === "pending";
  const canEdit = status === "pending";
  const canCancel = status === "running";
  const canDelete = status !== "running";

  return (
    <Card
      size="small"
      className="task-card"
      title={
        <Space>
          <Text ellipsis style={{ maxWidth: 300 }}>
            {task.message || task.name || task.id}
          </Text>
          <Tag color={config.color} icon={config.icon}>
            {config.text}
          </Tag>
        </Space>
      }
      extra={
        <Space>
          {canStart && (
            <Button
              size="small"
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleStart}
              loading={startMutation.isPending}
            >
              {t("tasks:card.start")}
            </Button>
          )}
          {canEdit && onEdit && (
            <Button size="small" icon={<EditOutlined />} onClick={onEdit}>
              {t("tasks:card.edit")}
            </Button>
          )}
          {canCancel && (
            <Button size="small" danger onClick={onCancel}>
              {t("tasks:card.cancel")}
            </Button>
          )}
          {isCompleted && outputPath && (
            <Tooltip title={outputPath}>
              <Button
                size="small"
                icon={<FolderOpenOutlined />}
                onClick={handleOpenLocation}
              />
            </Tooltip>
          )}
          {canDelete && (
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={onDelete}
            />
          )}
        </Space>
      }
    >
      {/* 进度条 */}
      {status === "running" && (
        <div style={{ marginBottom: 8 }}>
          <Progress
            percent={Math.round(task.progress || 0)}
            status="active"
            size="small"
          />
          <Text type="secondary">{task.message || ""}</Text>
        </div>
      )}

      {/* 错误信息 */}
      {status === "failed" && task.error && (
        <Text type="danger" ellipsis={{ tooltip: true }} style={{ display: "block" }}>
          {task.error}
        </Text>
      )}

      {/* 完成后的输出文件 */}
      {isCompleted && outputPath && (
        <Tooltip title={outputPath}>
          <Text type="secondary" ellipsis style={{ display: "block" }}>
            {outputPath}
          </Text>
        </Tooltip>
      )}
    </Card>
  );
};

export default TaskCard;
