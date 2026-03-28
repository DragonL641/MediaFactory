/**
 * 页面头部共享组件
 *
 * 统一所有页面的标题栏结构，包含标题、描述和操作区
 */

import React from "react";

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
    <div className="page-header">
      <div className="page-header-left">
        <h1 className="page-header-title">{title}</h1>
        {description && <p className="page-header-description">{description}</p>}
      </div>
      {actions && <div className="action-buttons">{actions}</div>}
    </div>
  );
};

export default PageHeader;
