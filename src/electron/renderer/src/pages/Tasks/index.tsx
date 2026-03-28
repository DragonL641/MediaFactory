/**
 * Tasks 页面
 *
 * 任务队列管理：创建、启动、编辑、取消、删除
 * 任务创建后不自动执行，需手动启动
 */

import React, { useState } from "react";
import {
  Button,
  Space,
  Popconfirm,
  App,
  Result,
} from "antd";
import {
  PlusOutlined,
  PlayCircleOutlined,
  StopOutlined,
  ClearOutlined,
  FileTextOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import {
  useTasksQuery,
  useCancelTaskMutation,
  useDeleteTaskMutation,
  useBatchStartMutation,
  useBatchCancelMutation,
  useBatchClearMutation,
} from "../../api/queries";
import type { Task, BatchOperationResponse } from "../../types";
import PageHeader from "../../components/Layout/PageHeader";
import { EmptyState, PageSkeleton } from "../../components/common";
import TaskCard from "./TaskCard";
import CreateTaskDialog from "./CreateTaskDialog";
import EditTaskDialog from "./EditTaskDialog";

const TasksPage: React.FC = () => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editTaskId, setEditTaskId] = useState<string | null>(null);
  const { message } = App.useApp();
  const { t } = useTranslation("tasks");

  const { data: tasks, isLoading, isError, refetch } = useTasksQuery();
  const cancelMutation = useCancelTaskMutation();
  const deleteMutation = useDeleteTaskMutation();
  const batchStartMutation = useBatchStartMutation();
  const batchCancelMutation = useBatchCancelMutation();
  const batchClearMutation = useBatchClearMutation();

  const handleCancel = (taskId: string) => {
    cancelMutation.mutate(taskId);
  };

  const handleDelete = (taskId: string) => {
    deleteMutation.mutate(taskId);
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

  if (isLoading) {
    return <PageSkeleton type="tasks" />;
  }

  if (isError) {
    return (
      <div style={{ padding: 48 }}>
        <Result
          status="error"
          title={t("tasks:error.loadFailed")}
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

  const taskList = Array.isArray(tasks) ? tasks : [];
  const hasPendingTasks = taskList.some((t: Task) => t.status === "pending");
  const hasRunningTasks = taskList.some((t: Task) => t.status === "running");
  const hasClearedTasks = taskList.some((t: Task) =>
    ["completed", "failed", "cancelled"].includes(t.status)
  );

  return (
    <div className="page-enter">
      <PageHeader
        title={t("tasks:pageHeader.title")}
        description={t("tasks:pageHeader.description")}
        actions={
          <Space size={8}>
            <Button
              icon={<PlusOutlined />}
              type="primary"
              onClick={() => setDialogOpen(true)}
            >
              {t("tasks:actions.addTask")}
            </Button>
            <Button
              icon={<PlayCircleOutlined />}
              onClick={handleBatchStart}
              loading={batchStartMutation.isPending}
              disabled={!hasPendingTasks}
            >
              {t("tasks:actions.startAll")}
            </Button>
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
              >
                {t("tasks:actions.cancelAll")}
              </Button>
            </Popconfirm>
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
              >
                {t("tasks:actions.clearAll")}
              </Button>
            </Popconfirm>
          </Space>
        }
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
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {taskList.map((task: Task) => (
            <TaskCard
              key={task.id}
              task={task}
              onCancel={() => handleCancel(task.id)}
              onDelete={() => handleDelete(task.id)}
              onEdit={() => setEditTaskId(task.id)}
            />
          ))}
        </div>
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
    </div>
  );
};

export default TasksPage;
