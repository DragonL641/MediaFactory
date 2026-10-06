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
  StopOutlined,
  FileTextOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { Task, TaskStatus } from "../../types";
import { useStartTaskMutation } from "../../api/queries";
import LogModal from "./LogModal";
import { getApiClient, getErrorDetail } from "../../api/client";

const { Text } = Typography;

interface TaskCardProps {
  task: Task;
  onCancel: () => void;
  onDelete: () => void;
  onRetry?: () => void;
  onEdit?: () => void;
}

const TaskCard: React.FC<TaskCardProps> = ({ task, onCancel, onDelete, onRetry, onEdit }) => {
  const [logOpen, setLogOpen] = React.useState(false);
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
    if (!outputPath) return;
    try {
      await getApiClient().post("/api/system/reveal", { path: outputPath });
    } catch {
      message.error(t("revealFailed"));
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
  const translationStats = task.metadata?.translation_stats as
    | { remote: number; fallback: number; failed: number }
    | undefined;
  const canStart = status === TaskStatus.PENDING;
  const canEdit = [TaskStatus.PENDING, TaskStatus.FAILED, TaskStatus.CANCELLED].includes(status);
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
            <Tooltip title={t("card.start")}>
              <Button size="small" type="primary" icon={<PlayCircleOutlined />} onClick={handleStart} loading={startMutation.isPending} />
            </Tooltip>
          )}
          {canEdit && onEdit && (
            <Tooltip title={t("card.edit")}>
              <Button size="small" icon={<EditOutlined />} onClick={onEdit} />
            </Tooltip>
          )}
          {canCancel && (
            <Tooltip title={t("card.cancel")}>
              <Button size="small" danger icon={<StopOutlined />} onClick={onCancel} />
            </Tooltip>
          )}
          {isCompleted && outputPath && (
            <Tooltip title={t("card.reveal")}>
              <Button size="small" icon={<FolderOpenOutlined />} onClick={handleOpenLocation} />
            </Tooltip>
          )}
          <Tooltip title={t("card.viewLog")}>
            <Button size="small" icon={<FileTextOutlined />} onClick={() => setLogOpen(true)} />
          </Tooltip>
          {canRetry && (
            <Tooltip title={t("card.retry")}>
              <Button size="small" icon={<RedoOutlined />} onClick={onRetry} />
            </Tooltip>
          )}
          {canDelete && (
            <Tooltip title={t("card.delete")}>
              <Popconfirm
                title={t("card.confirmDelete")}
                onConfirm={onDelete}
                okText={t("actions.confirm", { ns: "common" })}
                cancelText={t("actions.cancel", { ns: "common" })}
              >
                <Button size="small" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            </Tooltip>
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

      {/* 翻译统计（R3：总数=远端+兜底+失败，失败句保留原文） */}
      {isCompleted && translationStats && (
        <Text type="secondary" style={{ display: "block", fontSize: 12 }}>
          {t("card.translationStats", {
            remote: translationStats.remote,
            fallback: translationStats.fallback,
            failed: translationStats.failed,
          })}
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

      <LogModal open={logOpen} onClose={() => setLogOpen(false)} task={task} />
    </div>
  );
};

export default TaskCard;
