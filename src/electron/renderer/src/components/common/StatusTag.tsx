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

const statusConfig: Record<
  StatusType,
  { className: string; icon: React.ReactNode; defaultText: string }
> = {
  success: {
    className: "status-tag status-tag-success",
    icon: <CheckCircleOutlined />,
    defaultText: "Ready",
  },
  warning: {
    className: "status-tag status-tag-warning",
    icon: <ExclamationCircleOutlined />,
    defaultText: "Warning",
  },
  error: {
    className: "status-tag status-tag-error",
    icon: <CloseCircleOutlined />,
    defaultText: "Failed",
  },
  processing: {
    className: "status-tag status-tag-processing",
    icon: <LoadingOutlined />,
    defaultText: "Processing",
  },
  pending: {
    className: "status-tag status-tag-default",
    icon: <ClockCircleOutlined />,
    defaultText: "Pending",
  },
  default: {
    className: "status-tag status-tag-default",
    icon: null,
    defaultText: "",
  },
};

const StatusTag: React.FC<StatusTagProps> = ({ status, text }) => {
  const config = statusConfig[status];
  return (
    <span className={config.className}>
      {config.icon}
      {text || config.defaultText}
    </span>
  );
};

export default StatusTag;
