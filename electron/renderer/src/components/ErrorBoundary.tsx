/**
 * React Error Boundary
 *
 * 捕获子组件树中的 JavaScript 错误，防止整个应用崩溃
 */

import React, { Component, ErrorInfo, ReactNode } from "react";
import { Button, Result } from "antd";
import { useTranslation } from "react-i18next";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("[ErrorBoundary] Caught error:", error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <ErrorBoundaryInner
          subTitle={this.state.error?.message}
          onReset={this.handleReset}
        />
      );
    }

    return this.props.children;
  }
}

/** 抽离内容以便使用 hooks */
const ErrorBoundaryInner: React.FC<{
  subTitle?: string;
  onReset: () => void;
}> = ({ subTitle, onReset }) => {
  const { t } = useTranslation("common");

  return (
    <Result
      status="error"
      title={t("error.title")}
      subTitle={subTitle || t("error.subTitle")}
      extra={
        <Button type="primary" onClick={onReset}>
          {t("error.tryAgain")}
        </Button>
      }
    />
  );
};

export default ErrorBoundary;
