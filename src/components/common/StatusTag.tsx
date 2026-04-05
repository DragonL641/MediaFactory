/**
 * 统一状态标签组件
 *
 * 用于展示各种状态，如 Ready、Processing、Error 等
 */

import React from "react";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";

export type StatusType =
  | "success"
  | "warning"
  | "error"
  | "processing"
  | "default"
  | "pending";

interface StatusTagProps {
  status: StatusType;
  text?: string;
}

const StatusTag: React.FC<StatusTagProps> = ({ status, text }) => {
  const { t } = useTranslation("common");

  const statusConfig: Record<
    StatusType,
    { className: string; icon: React.ReactNode; defaultText: string }
  > = {
    success: {
      className: "status-tag status-tag-success",
      icon: <CheckCircleOutlined />,
      defaultText: t("status.ready"),
    },
    warning: {
      className: "status-tag status-tag-warning",
      icon: <ExclamationCircleOutlined />,
      defaultText: t("status.warning"),
    },
    error: {
      className: "status-tag status-tag-error",
      icon: <CloseCircleOutlined />,
      defaultText: t("status.failed"),
    },
    processing: {
      className: "status-tag status-tag-processing",
      icon: <LoadingOutlined />,
      defaultText: t("status.processing"),
    },
    pending: {
      className: "status-tag status-tag-default",
      icon: <ClockCircleOutlined />,
      defaultText: t("status.pending"),
    },
    default: {
      className: "status-tag status-tag-default",
      icon: null,
      defaultText: "",
    },
  };

  const config = statusConfig[status];
  return (
    <span className={config.className}>
      {config.icon}
      {text || config.defaultText}
    </span>
  );
};

export default StatusTag;
