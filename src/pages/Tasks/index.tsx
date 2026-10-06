/**
 * Tasks 页面
 *
 * 任务队列管理（表格视图）：类型/名称/时间/状态/进度/操作六列，
 * 类型+状态过滤与名称搜索；创建、启动、编辑、取消、删除、重试
 * 任务创建后不自动执行，需手动启动
 */

import React, { useMemo, useState } from "react";
import {
  Button,
  Space,
  Popconfirm,
  App,
  Alert,
  Select,
  Input,
  Table,
  Progress,
  Tag,
  Tooltip,
} from "antd";
import {
  PlusOutlined,
  PlayCircleOutlined,
  StopOutlined,
  ClearOutlined,
  FileTextOutlined,
  ClockCircleOutlined,
  LoadingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  PauseCircleOutlined,
  FolderOpenOutlined,
  DeleteOutlined,
  EditOutlined,
  RedoOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import {
  useTasksQuery,
  useStartTaskMutation,
  useCancelTaskMutation,
  useDeleteTaskMutation,
  useRetryTaskMutation,
  useBatchStartMutation,
  useBatchCancelMutation,
  useBatchClearMutation,
  useModelReadinessQuery,
} from "../../api/queries";
import { TaskStatus, type Task, type BatchOperationResponse } from "../../types";
import PageHeader from "../../components/Layout/PageHeader";
import { EmptyState, PageSkeleton, ErrorPage } from "../../components/common";
import LogModal from "./LogModal";
import CreateTaskDialog from "./CreateTaskDialog";
import EditTaskDialog from "./EditTaskDialog";
import { filterTasks, formatRelativeTime, TYPE_TAG_COLORS } from "./taskTableUtils";
import { getApiClient, getErrorDetail } from "../../api/client";

const TASK_TYPE_KEYS = ["audio", "transcribe", "translate", "subtitle", "enhance"];

// 状态值 → i18n 键尾（card.status.*）
const STATUS_KEY: Record<string, string> = {
  pending: "pending",
  running: "running",
  completed: "completed",
  failed: "failed",
  cancelled: "cancelled",
};

const TasksPage: React.FC = () => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editTaskId, setEditTaskId] = useState<string | null>(null);
  const [logTaskId, setLogTaskId] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const { message } = App.useApp();
  const { t } = useTranslation("tasks");

  const { data: tasks, isLoading, isError, refetch } = useTasksQuery();
  const startMutation = useStartTaskMutation();
  const cancelMutation = useCancelTaskMutation();
  const deleteMutation = useDeleteTaskMutation();
  const batchStartMutation = useBatchStartMutation();
  const batchCancelMutation = useBatchCancelMutation();
  const batchClearMutation = useBatchClearMutation();
  const retryMutation = useRetryTaskMutation();

  const { data: readiness } = useModelReadinessQuery();
  const navigate = useNavigate();

  const readinessWarnings = React.useMemo(() => {
    if (!readiness) return [];
    const warnings: { key: string; message: string; affectedTypes: string[] }[] = [];
    if (!readiness.whisper_ready) {
      warnings.push({
        key: "whisper",
        message: t("tasks:readiness.whisperWarning"),
        affectedTypes: ["Subtitle", "Transcribe"],
      });
    }
    if (!readiness.enhancement_ready) {
      warnings.push({ key: "enhancement", message: t("tasks:readiness.enhancementWarning"), affectedTypes: ["Enhance"] });
    }
    return warnings;
  }, [readiness, t]);

  const handleCancel = (taskId: string) => {
    cancelMutation.mutate(taskId);
  };

  const handleDelete = (taskId: string) => {
    deleteMutation.mutate(taskId);
  };

  const handleRetry = (taskId: string) => {
    retryMutation.mutate(taskId, {
      onSuccess: () => {
        message.success(t("tasks:card.retried"));
      },
      onError: () => {
        message.error(t("tasks:card.retryFailed"));
      },
    });
  };

  const handleBatchStart = () => {
    batchStartMutation.mutate(undefined, {
      onSuccess: (data: BatchOperationResponse) => {
        message.success(t("tasks:messages.queued", { count: data.started }));
      },
    });
  };

  const handleBatchCancel = () => {
    batchCancelMutation.mutate(undefined, {
      onSuccess: (data: BatchOperationResponse) => {
        message.success(t("tasks:messages.cancelled", { count: data.cancelled }));
      },
    });
  };

  const handleBatchClear = () => {
    batchClearMutation.mutate(undefined, {
      onSuccess: (data: BatchOperationResponse) => {
        message.success(t("tasks:messages.cleared", { count: data.cleared }));
      },
    });
  };

  const taskList = useMemo(() => (Array.isArray(tasks) ? tasks : []), [tasks]);
  const filteredTasks = useMemo(
    () => filterTasks(taskList, typeFilter, statusFilter, searchQuery),
    [taskList, typeFilter, statusFilter, searchQuery]
  );
  const logTask = useMemo(
    () => taskList.find((t: Task) => t.id === logTaskId),
    [taskList, logTaskId]
  );

  const hasPendingTasks = taskList.some((t: Task) => t.status === TaskStatus.PENDING);
  const hasRunningTasks = taskList.some((t: Task) => t.status === TaskStatus.RUNNING);
  const hasClearedTasks = taskList.some((t: Task) =>
    [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED].includes(t.status)
  );

  const statusConfig: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
    [TaskStatus.PENDING]: { color: "default", icon: <ClockCircleOutlined />, text: t("card.status.pending") },
    [TaskStatus.RUNNING]: { color: "processing", icon: <LoadingOutlined spin />, text: t("card.status.running") },
    [TaskStatus.COMPLETED]: { color: "success", icon: <CheckCircleOutlined />, text: t("card.status.completed") },
    [TaskStatus.FAILED]: { color: "error", icon: <CloseCircleOutlined />, text: t("card.status.failed") },
    [TaskStatus.CANCELLED]: { color: "warning", icon: <PauseCircleOutlined />, text: t("card.status.cancelled") },
  };

  if (isLoading) {
    return <PageSkeleton type="tasks" />;
  }

  if (isError) {
    return <ErrorPage title={t("tasks:error.loadFailed")} onRetry={() => refetch()} />;
  }

  const renderActions = (task: Task) => {
    const status = task.status;
    const canStart = status === TaskStatus.PENDING;
    const canEdit = [TaskStatus.PENDING, TaskStatus.FAILED, TaskStatus.CANCELLED].includes(status);
    const canCancel = status === TaskStatus.RUNNING;
    const canDelete = status !== TaskStatus.RUNNING;
    const canRetry = status === TaskStatus.FAILED || status === TaskStatus.CANCELLED;
    const canReveal = status === TaskStatus.COMPLETED && task.outputPath;

    const handleStart = () => {
      startMutation.mutate(task.id, {
        onSuccess: () => message.success(t("card.started")),
        onError: (error: unknown) => message.error(getErrorDetail(error) || t("card.startFailed")),
      });
    };

    const handleOpenLocation = async () => {
      if (!task.outputPath) return;
      try {
        await getApiClient().post("/api/system/reveal", { path: task.outputPath });
      } catch {
        message.error(t("revealFailed"));
      }
    };

    return (
      <Space size={4}>
        {canStart && (
          <Tooltip title={t("card.start")}>
            <Button size="small" type="primary" icon={<PlayCircleOutlined />} onClick={handleStart} loading={startMutation.isPending && startMutation.variables === task.id} />
          </Tooltip>
        )}
        {canEdit && (
          <Tooltip title={t("card.edit")}>
            <Button size="small" icon={<EditOutlined />} onClick={() => setEditTaskId(task.id)} />
          </Tooltip>
        )}
        {canCancel && (
          <Tooltip title={t("card.cancel")}>
            <Button size="small" danger icon={<StopOutlined />} onClick={() => handleCancel(task.id)} />
          </Tooltip>
        )}
        {canReveal && (
          <Tooltip title={t("card.reveal")}>
            <Button size="small" icon={<FolderOpenOutlined />} onClick={handleOpenLocation} />
          </Tooltip>
        )}
        <Tooltip title={t("card.viewLog")}>
          <Button size="small" icon={<FileTextOutlined />} onClick={() => setLogTaskId(task.id)} />
        </Tooltip>
        {canRetry && (
          <Tooltip title={t("card.retry")}>
            <Button size="small" icon={<RedoOutlined />} onClick={() => handleRetry(task.id)} />
          </Tooltip>
        )}
        {canDelete && (
          <Tooltip title={t("card.delete")}>
            <Popconfirm
              title={t("card.confirmDelete")}
              onConfirm={() => handleDelete(task.id)}
              okText={t("actions.confirm", { ns: "common" })}
              cancelText={t("actions.cancel", { ns: "common" })}
            >
              <Button size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          </Tooltip>
        )}
      </Space>
    );
  };

  return (
    <div className="page-enter">
      <PageHeader
        title={t("tasks:pageHeader.title")}
        description={t("tasks:pageHeader.description")}
      />

      {taskList.length === 0 ? (
        <EmptyState
          icon={<FileTextOutlined />}
          title={t("tasks:empty.title")}
          description={t("tasks:empty.description")}
          actionText={t("tasks:empty.actionText")}
          onAction={() => setDialogOpen(true)}
        />
      ) : (
        <>
          <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap", alignItems: "center" }}>
            <span style={{ color: "var(--mf-text-secondary, #999)", fontSize: 13 }}>
              {t("tasks:filters.type")}
            </span>
            <Select
              value={typeFilter}
              onChange={setTypeFilter}
              style={{ width: 130 }}
              options={[
                { value: "all", label: t("tasks:filters.all") },
                ...TASK_TYPE_KEYS.map((k) => ({
                  value: k,
                  label: t(`tasks:typeOptions.${k}.title`),
                })),
              ]}
            />
            <span style={{ color: "var(--mf-text-secondary, #999)", fontSize: 13 }}>
              {t("tasks:filters.status")}
            </span>
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: 130 }}
              options={[
                { value: "all", label: t("tasks:filters.all") },
                ...Object.keys(STATUS_KEY).map((s) => ({
                  value: s,
                  label: t(`tasks:card.status.${STATUS_KEY[s]}`),
                })),
              ]}
            />
            <Input.Search
              placeholder={t("tasks:filters.searchPlaceholder")}
              allowClear
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ width: 220 }}
            />
            <Space size={4} style={{ marginLeft: "auto" }}>
              <Tooltip title={t("tasks:actions.addTask")}>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setDialogOpen(true)} />
              </Tooltip>
              <Tooltip title={t("tasks:actions.startAll")}>
                <Button
                  icon={<PlayCircleOutlined />}
                  onClick={handleBatchStart}
                  loading={batchStartMutation.isPending}
                  disabled={!hasPendingTasks}
                />
              </Tooltip>
              <Tooltip title={t("tasks:actions.cancelAll")}>
                <Popconfirm
                  title={t("tasks:confirm.cancelRunning.title")}
                  description={t("tasks:confirm.cancelRunning.description")}
                  onConfirm={handleBatchCancel}
                  okText={t("common:actions.cancel")}
                  cancelText={t("common:actions.back")}
                  okButtonProps={{ danger: true }}
                  disabled={!hasRunningTasks}
                >
                  <Button
                    icon={<StopOutlined />}
                    loading={batchCancelMutation.isPending}
                    disabled={!hasRunningTasks}
                  />
                </Popconfirm>
              </Tooltip>
              <Tooltip title={t("tasks:actions.clearAll")}>
                <Popconfirm
                  title={t("tasks:confirm.clearFinished.title")}
                  description={t("tasks:confirm.clearFinished.description")}
                  onConfirm={handleBatchClear}
                  okText={t("common:actions.delete")}
                  cancelText={t("common:actions.cancel")}
                  okButtonProps={{ danger: true }}
                  disabled={!hasClearedTasks}
                >
                  <Button
                    icon={<ClearOutlined />}
                    loading={batchClearMutation.isPending}
                    disabled={!hasClearedTasks}
                  />
                </Popconfirm>
              </Tooltip>
            </Space>
          </div>

          <Table
            rowKey="id"
            dataSource={filteredTasks}
            size="middle"
            pagination={false}
            scroll={{ x: "max-content" }}
            locale={{
              emptyText: t("tasks:filters.noMatch"),
            }}
          >
            <Table.Column
              title={t("tasks:columns.type")}
              dataIndex="type"
              key="type"
              width={110}
              render={(type: string) => (
                <Tag color={TYPE_TAG_COLORS[type] || "default"}>
                  {t(`tasks:typeOptions.${type}.title`)}
                </Tag>
              )}
            />
            <Table.Column
              title={t("tasks:columns.name")}
              key="name"
              render={(_unused, record: Task) => (
                <Tooltip title={record.name}>
                  <span
                    style={{
                      fontWeight: 500,
                      display: "inline-block",
                      maxWidth: "100%",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      verticalAlign: "bottom",
                    }}
                  >
                    {record.name || record.id}
                  </span>
                </Tooltip>
              )}
            />
            <Table.Column
              title={t("tasks:columns.createdAt")}
              key="createdAt"
              width={110}
              render={(_unused, record: Task) => (
                <Tooltip
                  title={
                    record.createdAt
                      ? new Date(record.createdAt * 1000).toLocaleString()
                      : undefined
                  }
                >
                  <span style={{ color: "var(--mf-text-secondary, #999)", fontSize: 12 }}>
                    {formatRelativeTime(record.createdAt)}
                  </span>
                </Tooltip>
              )}
            />
            <Table.Column
              title={t("tasks:columns.status")}
              key="status"
              width={120}
              render={(_unused, record: Task) => {
                const config = statusConfig[record.status] || statusConfig[TaskStatus.PENDING];
                return (
                  <Tag color={config.color} icon={config.icon}>
                    {config.text}
                  </Tag>
                );
              }}
            />
            <Table.Column
              title={t("tasks:columns.progress")}
              key="progress"
              width={140}
              render={(_unused, record: Task) =>
                record.status === TaskStatus.RUNNING ? (
                  <Progress percent={Math.round(record.progress)} size="small" />
                ) : (
                  <span style={{ color: "var(--mf-text-secondary, #999)" }}>—</span>
                )
              }
            />
            <Table.Column
              title={t("tasks:columns.actions")}
              key="actions"
              width={200}
              fixed="right"
              render={(_unused, record: Task) => renderActions(record)}
            />
          </Table>
        </>
      )}

      {readinessWarnings.length > 0 && (
        <Alert
          type="warning"
          showIcon
          style={{ marginTop: 12, padding: "8px 12px" }}
          title={<span style={{ fontSize: 12 }}>{t("tasks:readiness.title")}</span>}
          description={
            <div style={{ fontSize: 12 }}>
              {readinessWarnings.map((w) => (
                <div key={w.key}>
                  {w.message} ({w.affectedTypes.join(", ")})
                </div>
              ))}
              <Button
                type="link"
                size="small"
                style={{ padding: 0, marginTop: 2, fontSize: 12 }}
                onClick={() => navigate("/settings")}
              >
                {t("tasks:readiness.goToSettings")}
              </Button>
            </div>
          }
        />
      )}

      <CreateTaskDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
      />

      {editTaskId && (
        <EditTaskDialog
          taskId={editTaskId}
          open={!!editTaskId}
          onClose={() => setEditTaskId(null)}
        />
      )}

      {logTask && (
        <LogModal
          open={!!logTaskId}
          onClose={() => setLogTaskId(null)}
          task={logTask}
        />
      )}
    </div>
  );
};

export default TasksPage;
