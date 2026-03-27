/**
 * 页面头部共享组件
 *
 * 统一所有页面的标题栏结构
 */

import React from "react";
import { Typography, Space } from "antd";

const { Title, Text } = Typography;

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
}

const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  description,
  actions,
}) => {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: description ? "flex-start" : "center",
        marginBottom: 24,
      }}
    >
      <div>
        <Title level={4} style={{ margin: 0 }}>
          {title}
        </Title>
        {description && (
          <Text type="secondary" style={{ fontSize: 14 }}>
            {description}
          </Text>
        )}
      </div>
      {actions && <Space>{actions}</Space>}
    </div>
  );
};

export default PageHeader;
