/**
 * 任务卡片组件
 *
 * Soft Bento 风格：圆角卡片，柔和阴影
 */

import React from "react";
import { Progress, Tag, Button, Space, Typography, Tooltip, App, Popconfirm } from "antd";
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
  RedoOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { Task, TaskStatus } from "../../types";
import { useStartTaskMutation } from "../../api/queries";
import { getErrorDetail } from "../../api/client";

const { Text } = Typography;

interface TaskCardProps {
  task: Task;
  onCancel: () => void;
  onDelete: () => void;
  onRetry?: () => void;
  onEdit?: () => void;
}

const TaskCard: React.FC<TaskCardProps> = ({ task, onCancel, onDelete, onRetry, onEdit }) => {
  const status = task.status;
  const startMutation = useStartTaskMutation();
  const { message } = App.useApp();
  const { t } = useTranslation("tasks");

  const statusConfig: Record<TaskStatus, { color: string; icon: React.ReactNode; text: string }> = {
    [TaskStatus.PENDING]: { color: "default", icon: <ClockCircleOutlined />, text: t("card.status.pending") },
    [TaskStatus.RUNNING]: { color: "processing", icon: <LoadingOutlined spin />, text: t("card.status.running") },
    [TaskStatus.COMPLETED]: { color: "success", icon: <CheckCircleOutlined />, text: t("card.status.completed") },
    [TaskStatus.FAILED]: { color: "error", icon: <CloseCircleOutlined />, text: t("card.status.failed") },
    [TaskStatus.CANCELLED]: { color: "warning", icon: <PauseCircleOutlined />, text: t("card.status.cancelled") },
  };

  const config = statusConfig[status] || statusConfig[TaskStatus.PENDING];

  const handleOpenLocation = async () => {
    const outputPath = task.outputPath;
    if (outputPath && window.electronAPI) {
      await window.electronAPI.openFileLocation(outputPath);
    }
  };

  const handleStart = () => {
    startMutation.mutate(task.id, {
      onSuccess: () => message.success(t("card.started")),
      onError: (error: unknown) => message.error(getErrorDetail(error) || t("card.startFailed")),
    });
  };

  const outputPath = task.outputPath;
  const isCompleted = status === TaskStatus.COMPLETED;
  const canStart = status === TaskStatus.PENDING;
  const canEdit = status === TaskStatus.PENDING;
  const canCancel = status === TaskStatus.RUNNING;
  const canDelete = status !== TaskStatus.RUNNING;
  const canRetry = (status === TaskStatus.FAILED || status === TaskStatus.CANCELLED) && onRetry;

  return (
    <div className="task-card" style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {/* 状态行：名称 + 标签 + 操作 */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flex: 1, minWidth: 0 }}>
          <Text ellipsis style={{ fontWeight: 500 }}>
            {task.name || task.id}
          </Text>
          <Tag color={config.color} icon={config.icon}>
            {config.text}
          </Tag>
        </div>
        <Space size={4}>
          {canStart && (
            <Button size="small" type="primary" icon={<PlayCircleOutlined />} onClick={handleStart} loading={startMutation.isPending}>
              {t("card.start")}
            </Button>
          )}
          {canEdit && onEdit && (
            <Button size="small" icon={<EditOutlined />} onClick={onEdit}>
              {t("card.edit")}
            </Button>
          )}
          {canCancel && (
            <Button size="small" danger onClick={onCancel}>
              {t("card.cancel")}
            </Button>
          )}
          {isCompleted && outputPath && (
            <Tooltip title={outputPath}>
              <Button size="small" icon={<FolderOpenOutlined />} onClick={handleOpenLocation} />
            </Tooltip>
          )}
          {canRetry && (
            <Button size="small" icon={<RedoOutlined />} onClick={onRetry}>
              {t("card.retry")}
            </Button>
          )}
          {canDelete && (
            <Popconfirm
              title={t("card.confirmDelete")}
              onConfirm={onDelete}
              okText={t("actions.confirm", { ns: "common" })}
              cancelText={t("card.cancel")}
            >
              <Button size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          )}
        </Space>
      </div>

      {/* 实时状态消息 */}
      {status === TaskStatus.RUNNING && task.message && (
        <Text type="secondary" ellipsis style={{ display: "block", fontSize: 12 }}>
          {task.message}
        </Text>
      )}

      {/* 进度条 */}
      {status === TaskStatus.RUNNING && (
        <div>
          <Progress percent={Math.round(task.progress || 0)} status="active" size="small" />
        </div>
      )}

      {/* 错误信息 */}
      {status === TaskStatus.FAILED && task.error && (
        <Text type="danger" ellipsis={{ tooltip: true }} style={{ display: "block", fontSize: 12 }}>
          {task.error}
        </Text>
      )}

      {/* 完成后的输出文件 */}
      {isCompleted && outputPath && (
        <Tooltip title={outputPath}>
          <Text type="secondary" ellipsis style={{ display: "block", fontSize: 12 }}>
            {outputPath}
          </Text>
        </Tooltip>
      )}
    </div>
  );
};

export default TaskCard;
