/**
 * 统一页面骨架屏组件
 *
 * 根据页面类型展示对应的骨架布局，模拟真实页面结构
 * 让用户在加载时能预知即将显示的内容布局
 */

import React from "react";
import { Card, Skeleton, Space } from "antd";

export type PageSkeletonType = "tasks" | "models" | "llm" | "settings";

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
  <Card className="content-card" style={{ marginBottom: 12 }}>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
      <div style={{ flex: 1 }}>
        <Skeleton.Input active size="small" style={{ width: 200, height: 20, marginBottom: 8 }} />
        <Skeleton.Input active size="small" style={{ width: 320, height: 16, marginBottom: 12 }} />
        <Skeleton.Input active size="small" style={{ width: "100%", maxWidth: 400, height: 8, borderRadius: 4 }} />
      </div>
      <Space>
        <Skeleton.Button active size="small" shape="circle" style={{ width: 32, height: 32 }} />
        <Skeleton.Button active size="small" shape="circle" style={{ width: 32, height: 32 }} />
      </Space>
    </div>
  </Card>
);

/**
 * 模型分组卡片骨架
 */
const ModelGroupSkeleton: React.FC<{ items?: number }> = ({ items = 3 }) => (
  <Card className="content-card" style={{ marginBottom: 24 }}>
    <div style={{ marginBottom: 16 }}>
      <Skeleton.Input active size="small" style={{ width: 140, height: 20, marginBottom: 4 }} />
      <Skeleton.Input active size="small" style={{ width: 280, height: 14 }} />
    </div>
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {Array.from({ length: items }).map((_, i) => (
        <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <Skeleton.Avatar active size={36} shape="square" style={{ borderRadius: 6 }} />
            <div>
              <Skeleton.Input active size="small" style={{ width: 120, height: 16, marginBottom: 4 }} />
              <Skeleton.Input active size="small" style={{ width: 80, height: 12 }} />
            </div>
          </div>
          <Skeleton.Button active size="small" style={{ width: 80 }} />
        </div>
      ))}
    </div>
  </Card>
);

/**
 * LLM Provider 卡片骨架
 */
const ProviderCardSkeleton: React.FC = () => (
  <Card className="content-card" style={{ marginBottom: 12 }}>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
          <Skeleton.Input active size="small" style={{ width: 140, height: 20 }} />
          <Skeleton.Button active size="small" style={{ width: 60, height: 22, borderRadius: 11 }} />
        </div>
        <Skeleton.Input active size="small" style={{ width: 220, height: 14 }} />
      </div>
      <Space>
        <Skeleton.Button active size="small" shape="circle" style={{ width: 32, height: 32 }} />
        <Skeleton.Button active size="small" shape="circle" style={{ width: 32, height: 32 }} />
        <Skeleton.Button active size="small" shape="circle" style={{ width: 32, height: 32 }} />
      </Space>
    </div>
  </Card>
);

/**
 * 设置表单骨架
 */
const SettingsFormSkeleton: React.FC = () => (
  <>
    <Card className="content-card" style={{ marginBottom: 24 }}>
      <Skeleton.Input active size="small" style={{ width: 160, height: 18, marginBottom: 16 }} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i}>
            <Skeleton.Input active size="small" style={{ width: 100, height: 14, marginBottom: 8 }} />
            <Skeleton.Input active size="default" style={{ width: "100%", height: 32 }} />
          </div>
        ))}
      </div>
    </Card>
    <Card className="content-card" style={{ marginBottom: 24 }}>
      <Skeleton.Input active size="small" style={{ width: 120, height: 18, marginBottom: 16 }} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i}>
            <Skeleton.Input active size="small" style={{ width: 80, height: 14, marginBottom: 8 }} />
            <Skeleton.Input active size="default" style={{ width: "100%", height: 32 }} />
          </div>
        ))}
      </div>
    </Card>
  </>
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

      case "models":
        return (
          <>
            <HeaderSkeleton hasActions={true} />
            <ModelGroupSkeleton items={2} />
            <ModelGroupSkeleton items={3} />
          </>
        );

      case "llm":
        return (
          <>
            <HeaderSkeleton />
            <ProviderCardSkeleton />
            <ProviderCardSkeleton />
            <ProviderCardSkeleton />
          </>
        );

      case "settings":
        return (
          <>
            <HeaderSkeleton hasActions={false} />
            <SettingsFormSkeleton />
          </>
        );

      default:
        return <Skeleton active paragraph={{ rows: 6 }} />;
    }
  };

  return <div className="page-enter">{renderContent()}</div>;
};

export default PageSkeleton;
