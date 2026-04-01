/**
 * 统一页面骨架屏组件
 *
 * 根据页面类型展示对应的骨架布局
 */

import React from "react";
import { Card, Skeleton, Space } from "antd";

export type PageSkeletonType = "tasks" | "settings";

interface PageSkeletonProps {
  type: PageSkeletonType;
}

/**
 * 页头骨架
 */
const HeaderSkeleton: React.FC<{ hasActions?: boolean }> = ({ hasActions = true }) => (
  <div className="page-header" style={{ marginBottom: 24 }}>
    <div className="page-header-left">
      <Skeleton.Input active size="large" style={{ width: 180, height: 28 }} />
      <Skeleton.Input active size="small" style={{ width: 280, height: 18, marginTop: 8 }} />
    </div>
    {hasActions && (
      <Space>
        <Skeleton.Button active size="default" style={{ width: 100 }} />
        <Skeleton.Button active size="default" style={{ width: 90 }} />
      </Space>
    )}
  </div>
);

/**
 * 任务卡片骨架
 */
const TaskCardSkeleton: React.FC = () => (
  <div className="task-card" style={{ marginBottom: 12 }}>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <Skeleton.Input active size="small" style={{ width: 200, height: 20 }} />
        <Skeleton.Button active size="small" style={{ width: 80, height: 22, borderRadius: 6 }} />
      </div>
      <Space>
        <Skeleton.Button active size="small" style={{ width: 60 }} />
        <Skeleton.Button active size="small" shape="circle" style={{ width: 28, height: 28 }} />
      </Space>
    </div>
  </div>
);

/**
 * 设置区块骨架
 */
const SettingsSectionSkeleton: React.FC<{ rows?: number }> = ({ rows = 3 }) => (
  <div className="settings-section-card" style={{ marginBottom: 24 }}>
    <Skeleton.Input active size="small" style={{ width: 160, height: 18, marginBottom: 16 }} />
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <Skeleton.Input active size="small" style={{ width: 120, height: 16, marginBottom: 4 }} />
            <Skeleton.Input active size="small" style={{ width: 80, height: 12 }} />
          </div>
          <Skeleton.Button active size="small" style={{ width: 80 }} />
        </div>
      ))}
    </div>
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 16 }}>
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i}>
          <Skeleton.Input active size="small" style={{ width: 100, height: 14, marginBottom: 8 }} />
          <Skeleton.Input active size="default" style={{ width: "100%", height: 32 }} />
        </div>
      ))}
    </div>
  </div>
);

/**
 * 根据页面类型渲染对应的骨架布局
 */
const PageSkeleton: React.FC<PageSkeletonProps> = ({ type }) => {
  const renderContent = () => {
    switch (type) {
      case "tasks":
        return (
          <>
            <HeaderSkeleton />
            <TaskCardSkeleton />
            <TaskCardSkeleton />
            <TaskCardSkeleton />
          </>
        );

      case "settings":
        return (
          <>
            <HeaderSkeleton hasActions={false} />
            <SettingsSectionSkeleton rows={1} />
            <SettingsSectionSkeleton rows={1} />
            <SettingsSectionSkeleton rows={2} />
            <SettingsSectionSkeleton rows={3} />
          </>
        );

      default:
        return <Skeleton active paragraph={{ rows: 6 }} />;
    }
  };

  return <div className="page-enter">{renderContent()}</div>;
};

export default PageSkeleton;
