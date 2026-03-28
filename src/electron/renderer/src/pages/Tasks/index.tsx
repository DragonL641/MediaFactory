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
  Spin,
  Result,
} from "antd";
import {
  PlusOutlined,
  PlayCircleOutlined,
  StopOutlined,
  ClearOutlined,
  FileTextOutlined,
} from "@ant-design/icons";
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
import { EmptyState } from "../../components/common";
import TaskCard from "./TaskCard";
import CreateTaskDialog from "./CreateTaskDialog";
import EditTaskDialog from "./EditTaskDialog";

const TasksPage: React.FC = () => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editTaskId, setEditTaskId] = useState<string | null>(null);
  const { message } = App.useApp();

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
        message.success(`Queued ${data.started} task(s)`);
      },
    });
  };

  const handleBatchCancel = () => {
    batchCancelMutation.mutate(undefined, {
      onSuccess: (data: BatchOperationResponse) => {
        message.success(`Cancelled ${data.cancelled} task(s)`);
      },
    });
  };

  const handleBatchClear = () => {
    batchClearMutation.mutate(undefined, {
      onSuccess: (data: BatchOperationResponse) => {
        message.success(`Cleared ${data.cleared} task(s)`);
      },
    });
  };

  if (isLoading) {
    return (
      <div style={{ textAlign: "center", padding: 48 }}>
        <Spin />
      </div>
    );
  }

  if (isError) {
    return (
      <div style={{ padding: 48 }}>
        <Result
          status="error"
          title="Failed to load tasks"
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

  const taskList = Array.isArray(tasks) ? tasks : [];
  const hasPendingTasks = taskList.some((t: Task) => t.status === "pending");
  const hasRunningTasks = taskList.some((t: Task) => t.status === "running");
  const hasClearedTasks = taskList.some((t: Task) =>
    ["completed", "failed", "cancelled"].includes(t.status)
  );

  return (
    <div className="page-enter">
      <PageHeader
        title="Task Queue"
        description="Manage and execute your media processing tasks"
        actions={
          <Space size={8}>
            <Button
              icon={<PlusOutlined />}
              type="primary"
              onClick={() => setDialogOpen(true)}
            >
              Add Task
            </Button>
            <Button
              icon={<PlayCircleOutlined />}
              onClick={handleBatchStart}
              loading={batchStartMutation.isPending}
              disabled={!hasPendingTasks}
            >
              Start All
            </Button>
            <Popconfirm
              title="Cancel running tasks?"
              description="This will stop all currently running tasks."
              onConfirm={handleBatchCancel}
              okText="Cancel Tasks"
              cancelText="Back"
              okButtonProps={{ danger: true }}
              disabled={!hasRunningTasks}
            >
              <Button
                icon={<StopOutlined />}
                loading={batchCancelMutation.isPending}
                disabled={!hasRunningTasks}
              >
                Cancel All
              </Button>
            </Popconfirm>
            <Popconfirm
              title="Clear finished tasks?"
              description="Remove all completed, failed, and cancelled tasks."
              onConfirm={handleBatchClear}
              okText="Clear"
              cancelText="Cancel"
              okButtonProps={{ danger: true }}
              disabled={!hasClearedTasks}
            >
              <Button
                icon={<ClearOutlined />}
                loading={batchClearMutation.isPending}
                disabled={!hasClearedTasks}
              >
                Clear All
              </Button>
            </Popconfirm>
          </Space>
        }
      />

      {taskList.length === 0 ? (
        <EmptyState
          icon={<FileTextOutlined />}
          title="No tasks yet"
          description="Create a task to start processing your media files"
          actionText="Add Task"
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
