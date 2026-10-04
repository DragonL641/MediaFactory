/**
 * 本地模型（Ollama）管理卡片：服务状态、已装模型、拉取、删除。
 * 拉取进度复用任务列表（pull 是 DOWNLOAD 类型任务，走既有 WS 通路）。
 */

import React, { useState } from "react";
import { App, Button, Input, Popconfirm, Table, Tag, theme } from "antd";
import { useTranslation } from "react-i18next";
import {
  useDeleteLocalModelMutation,
  useLocalModelsQuery,
  usePullLocalModelMutation,
} from "../../api/queries";
import { getErrorDetail } from "../../api/client";
import type { LocalModelInfo } from "../../types";

function formatSize(bytes: number): string {
  if (bytes >= 1024 ** 3) return `${(bytes / 1024 ** 3).toFixed(1)} GB`;
  if (bytes >= 1024 ** 2) return `${Math.round(bytes / 1024 ** 2)} MB`;
  return `${bytes} B`;
}

const LocalModelsCard: React.FC = () => {
  const { t } = useTranslation("settings");
  const { message } = App.useApp();
  const { token } = theme.useToken();
  const { data, isLoading } = useLocalModelsQuery();
  const pullMutation = usePullLocalModelMutation();
  const deleteMutation = useDeleteLocalModelMutation();
  const [modelName, setModelName] = useState("");

  const handlePull = async () => {
    const name = modelName.trim();
    if (!name) return;
    try {
      await pullMutation.mutateAsync(name);
      setModelName("");
      message.success(t("localModels.pullStarted"));
    } catch (error) {
      message.error(getErrorDetail(error) || t("localModels.pullFailed"));
    }
  };

  const handleDelete = async (name: string) => {
    try {
      await deleteMutation.mutateAsync(name);
      message.success(t("localModels.deleted"));
    } catch (error) {
      message.error(getErrorDetail(error) || t("localModels.deleteFailed"));
    }
  };

  const columns = [
    { title: t("localModels.columnName"), dataIndex: "name", key: "name" },
    {
      title: t("localModels.columnSize"),
      dataIndex: "size",
      key: "size",
      render: (size: number) => formatSize(size),
    },
    {
      title: t("localModels.columnParams"),
      dataIndex: "parameterSize",
      key: "parameterSize",
    },
    {
      title: t("localModels.columnQuant"),
      dataIndex: "quantizationLevel",
      key: "quantizationLevel",
    },
    {
      title: "",
      key: "actions",
      render: (_: unknown, record: LocalModelInfo) => (
        <Popconfirm
          title={t("localModels.deleteConfirm", { name: record.name })}
          onConfirm={() => handleDelete(record.name)}
        >
          <Button size="small" danger loading={deleteMutation.isPending}>
            {t("localModels.delete")}
          </Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <div className="settings-section-card" style={{ marginBottom: 24 }}>
      <h3>{t("localModels.title")}</h3>
      <p style={{ color: token.colorTextSecondary }}>
        {t("localModels.description")}{" "}
        <a href="https://ollama.com/library" target="_blank" rel="noreferrer">
          ollama.com/library
        </a>
      </p>

      <div style={{ marginBottom: 12 }}>
        {data?.available ? (
          <Tag color="success">{t("localModels.running")}</Tag>
        ) : (
          <Tag color="default">{t("localModels.notDetected")}</Tag>
        )}
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <Input
          style={{ maxWidth: 320 }}
          value={modelName}
          onChange={(e) => setModelName(e.target.value)}
          placeholder={t("localModels.pullPlaceholder")}
          disabled={!data?.available}
          onPressEnter={handlePull}
        />
        <Button
          type="primary"
          onClick={handlePull}
          loading={pullMutation.isPending}
          disabled={!data?.available || !modelName.trim()}
        >
          {t("localModels.pull")}
        </Button>
      </div>

      <Table
        size="small"
        rowKey="name"
        loading={isLoading}
        dataSource={data?.models ?? []}
        columns={columns}
        pagination={false}
        locale={{ emptyText: t("localModels.empty") }}
      />
    </div>
  );
};

export default LocalModelsCard;
