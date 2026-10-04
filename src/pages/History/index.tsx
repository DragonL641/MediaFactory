/**
 * 任务历史页面
 *
 * 展示已完成任务的终态历史（独立于任务队列，清除任务不影响历史）。
 * 服务端分页，WebSocket 任务完成时由 WebSocketBridge 失效刷新。
 */

import React, { useState } from "react";
import { Button, Popconfirm, Table, Tooltip, Typography } from "antd";
import type { ColumnsType, TablePaginationConfig } from "antd/es/table";
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  HistoryOutlined,
  RedoOutlined,
  RestOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { useHistoryQuery, useClearHistoryMutation } from "../../api/queries";
import type { TaskHistoryRecord } from "../../types";
import PageHeader from "../../components/Layout/PageHeader";
import { EmptyState } from "../../components/common";

const HistoryPage: React.FC = () => {
  const { t } = useTranslation("history");
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const { data, isLoading, isFetching, refetch } = useHistoryQuery({
    limit: pageSize,
    offset: (page - 1) * pageSize,
  });
  const clearHistory = useClearHistoryMutation();

  const formatTime = (iso: string): string => {
    const d = new Date(iso);
    return isNaN(d.getTime()) ? iso : d.toLocaleString();
  };

  const formatDuration = (ms: number | null): string => {
    if (ms === null) return "-";
    if (ms < 1000) return `${ms}ms`;
    const s = ms / 1000;
    if (s < 60) return `${s.toFixed(1)}s`;
    const m = Math.floor(s / 60);
    return `${m}m ${Math.round(s % 60)}s`;
  };

  const statusIcon = (status: string): React.ReactNode => {
    if (status === "completed") return <CheckCircleOutlined />;
    if (status === "failed") return <CloseCircleOutlined />;
    if (status === "cancelled") return <ExclamationCircleOutlined />;
    return <ClockCircleOutlined />;
  };

  const columns: ColumnsType<TaskHistoryRecord> = [
    {
      title: t("columns.name"),
      dataIndex: "name",
      ellipsis: true,
    },
    {
      title: t("columns.type"),
      dataIndex: "type",
      width: 110,
    },
    {
      title: t("columns.status"),
      dataIndex: "status",
      width: 130,
      render: (status: string) => (
        <span
          className={`status-tag status-tag-${
            status === "completed" ? "success" : status === "failed" ? "error" : "warning"
          }`}
        >
          {statusIcon(status)}
          {t(`status.${status}`, status)}
        </span>
      ),
    },
    {
      title: t("columns.completedAt"),
      dataIndex: "completedAt",
      width: 180,
      render: (iso: string) => formatTime(iso),
    },
    {
      title: t("columns.duration"),
      dataIndex: "durationMs",
      width: 100,
      render: (ms: number | null) => formatDuration(ms),
    },
    {
      title: t("columns.outputPath"),
      dataIndex: "outputPath",
      ellipsis: true,
      render: (path: string | null) =>
        path ? (
          <Tooltip title={path}>
            <Typography.Text code style={{ fontSize: 12 }}>
              {path}
            </Typography.Text>
          </Tooltip>
        ) : (
          "-"
        ),
    },
    {
      title: t("columns.stats"),
      dataIndex: "metadata",
      key: "stats",
      render: (_: unknown, record: TaskHistoryRecord) => {
        const stats = record.metadata?.translation_stats as
          | { total: number; remote: number; fallback: number; failed: number }
          | undefined;
        if (!stats) return "-";
        return `Translated ${stats.remote} · Fallback ${stats.fallback} · Failed ${stats.failed}`;
      },
    },
    {
      title: t("columns.error"),
      dataIndex: "error",
      ellipsis: true,
      render: (error: string | null) =>
        error ? (
          <Tooltip title={error}>
            <Typography.Text type="danger" style={{ fontSize: 12 }}>
              {error}
            </Typography.Text>
          </Tooltip>
        ) : (
          "-"
        ),
    },
  ];

  const pagination: TablePaginationConfig = {
    current: page,
    pageSize,
    total: data?.total ?? 0,
    showSizeChanger: false,
    onChange: (p) => setPage(p),
  };

  const isEmpty = isLoading || !data || data.items.length === 0;

  return (
    <div className="page-enter">
      <PageHeader
        title={t("title")}
        description={t("subtitle")}
        actions={
          <>
            <Button
              icon={<RedoOutlined />}
              onClick={() => void refetch()}
              loading={isFetching}
            >
              {t("actions.refresh")}
            </Button>
            <Popconfirm
              title={t("actions.clearConfirm")}
              onConfirm={() => {
                clearHistory.mutate();
                setPage(1);
              }}
              disabled={isEmpty}
            >
              <Button icon={<RestOutlined />} danger disabled={isEmpty}>
                {t("actions.clear")}
              </Button>
            </Popconfirm>
          </>
        }
      />

      {isLoading ? (
        <Table loading rowKey="taskId" columns={columns} dataSource={[]} />
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          icon={<HistoryOutlined />}
          title={t("empty.title")}
          description={t("empty.description")}
        />
      ) : (
        <Table
          rowKey="taskId"
          columns={columns}
          dataSource={data.items}
          pagination={pagination}
          loading={isFetching}
        />
      )}
    </div>
  );
};

export default HistoryPage;
