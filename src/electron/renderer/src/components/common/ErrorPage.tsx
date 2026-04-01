/**
 * 错误页面组件
 *
 * 统一的错误状态展示，用于页面级错误（加载失败等）
 */

import React from "react";
import { Result, Button } from "antd";
import { useTranslation } from "react-i18next";

interface ErrorPageProps {
  title: string;
  onRetry: () => void;
}

const ErrorPage: React.FC<ErrorPageProps> = ({ title, onRetry }) => {
  const { t } = useTranslation();
  return (
    <div style={{ padding: 48 }}>
      <Result
        status="error"
        title={title}
        subTitle={t("common:error.connectFailed")}
        extra={
          <Button type="primary" onClick={onRetry}>
            {t("common:error.retry")}
          </Button>
        }
      />
    </div>
  );
};

export default ErrorPage;
