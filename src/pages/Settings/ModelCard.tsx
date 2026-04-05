/**
 * 统一模型卡片组件
 *
 * 用于 Settings 页面中所有模型展示
 * 支持 Ready / Downloading / Failed / Incomplete / Not Downloaded 五种状态
 */

import React from "react";
import { Button, Popconfirm, Progress, Tooltip } from "antd";
import { DeleteOutlined, DownloadOutlined, ExclamationCircleOutlined, RedoOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { StatusTag } from "../../components/common";

export interface ModelCardProps {
  /** 功能描述标题 */
  name: string;
  /** 副标题（模型名称 + 规格） */
  subtitle?: string;
  /** 是否已下载 */
  downloaded: boolean;
  /** 是否完整下载 */
  complete?: boolean;
  /** 是否正在下载 */
  isDownloading?: boolean;
  /** 下载进度 (0-100) */
  downloadProgress?: number;
  /** 下载失败原因 */
  downloadError?: string;
  /** 禁用下载按钮（其他模型正在下载时） */
  downloadDisabled?: boolean;
  /** 下载回调 */
  onDownload?: () => void;
  /** 删除回调 */
  onDelete?: () => void;
}

const SettingsModelCard: React.FC<ModelCardProps> = ({
  name,
  subtitle,
  downloaded,
  complete,
  isDownloading,
  downloadProgress,
  downloadError,
  downloadDisabled,
  onDownload,
  onDelete,
}) => {
  const { t } = useTranslation("models");

  const isReady = downloaded && complete !== false;
  const isIncomplete = downloaded && complete === false;
  const isFailed = !isDownloading && !!downloadError;

  return (
    <div className="model-card">
      <div className="model-card-header">
        <div>
          <div className="model-card-name">{name}</div>
          {subtitle && <div className="model-card-meta">{subtitle}</div>}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {isDownloading ? (
            <div style={{ width: 120 }}>
              <Progress
                percent={downloadProgress || 0}
                size="small"
                format={(percent) => `${percent}%`}
              />
            </div>
          ) : isReady ? (
            <>
              <StatusTag status="success" text={t("card.ready")} />
              {onDelete && (
                <Popconfirm
                  title={t("confirm.deleteTitle")}
                  description={t("confirm.deleteDescription", { name })}
                  onConfirm={onDelete}
                  okText={t("common:actions.delete", { ns: "common" })}
                  cancelText={t("common:actions.cancel", { ns: "common" })}
                  okButtonProps={{ danger: true }}
                >
                  <Tooltip title={t("card.delete")}>
                    <Button size="small" type="text" danger icon={<DeleteOutlined />} />
                  </Tooltip>
                </Popconfirm>
              )}
            </>
          ) : isFailed ? (
            <>
              {onDownload && (
                <Button
                  size="small"
                  type="link"
                  icon={<RedoOutlined />}
                  onClick={onDownload}
                  disabled={downloadDisabled}
                >
                  {t("card.retry")}
                </Button>
              )}
              <Tooltip title={downloadError || t("card.downloadFailed")}>
                <ExclamationCircleOutlined style={{ color: "#ff4d4f", fontSize: 16, cursor: "pointer" }} />
              </Tooltip>
            </>
          ) : isIncomplete ? (
            <>
              <Tooltip title={t("card.incompleteTooltip")}>
                <StatusTag status="warning" text={t("card.incomplete")} />
              </Tooltip>
              {onDownload && (
                <Button
                  size="small"
                  type="link"
                  icon={<RedoOutlined />}
                  onClick={onDownload}
                  disabled={downloadDisabled}
                >
                  {t("card.retry")}
                </Button>
              )}
              {onDelete && (
                <Popconfirm
                  title={t("confirm.deleteTitle")}
                  description={t("confirm.deleteDescription", { name })}
                  onConfirm={onDelete}
                  okText={t("common:actions.delete", { ns: "common" })}
                  cancelText={t("common:actions.cancel", { ns: "common" })}
                  okButtonProps={{ danger: true }}
                >
                  <Button size="small" type="text" danger icon={<DeleteOutlined />} />
                </Popconfirm>
              )}
            </>
          ) : (
            onDownload && (
              <Button
                size="small"
                type="primary"
                icon={<DownloadOutlined />}
                onClick={onDownload}
                disabled={downloadDisabled}
              >
                {t("card.download")}
              </Button>
            )
          )}
        </div>
      </div>
    </div>
  );
};

export default SettingsModelCard;
