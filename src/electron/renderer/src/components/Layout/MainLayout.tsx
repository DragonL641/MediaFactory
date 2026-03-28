/**
 * 主布局组件
 *
 * 包含侧边栏导航和主内容区域，支持侧边栏折叠
 */

import React, { useState } from "react";
import { Layout, Menu, Typography, theme, Button, Tooltip } from "antd";
import {
  FileTextOutlined,
  CloudServerOutlined,
  CloudOutlined,
  SettingOutlined,
  LeftOutlined,
  RightOutlined,
} from "@ant-design/icons";
import { useNavigate, useLocation } from "react-router-dom";

const { Sider, Content } = Layout;
const { Text } = Typography;

interface MainLayoutProps {
  children: React.ReactNode;
}

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const {
    token: { colorBgContainer, borderRadiusLG, colorPrimary, colorBgElevated },
  } = theme.useToken();

  const menuItems = [
    {
      key: "/tasks",
      icon: <FileTextOutlined />,
      label: "Tasks",
    },
    {
      key: "/models",
      icon: <CloudServerOutlined />,
      label: "Models",
    },
    {
      key: "/llm-config",
      icon: <CloudOutlined />,
      label: "LLM Config",
    },
    {
      key: "/settings",
      icon: <SettingOutlined />,
      label: "Settings",
    },
  ];

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
  };

  const siderWidth = collapsed ? 72 : 200;

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider
        width={200}
        collapsedWidth={72}
        collapsed={collapsed}
        trigger={null}
        style={{
          overflow: "auto",
          height: "100vh",
          position: "fixed",
          left: 0,
          top: 0,
          bottom: 0,
          borderRight: "1px solid #F3F4F6",
          zIndex: 10,
          transition: "width 0.2s ease",
        }}
      >
        {/* Logo区域 - 更简洁 */}
        <div
          style={{
            height: 56,
            margin: "12px 12px 8px",
            display: "flex",
            alignItems: "center",
            justifyContent: collapsed ? "center" : "flex-start",
            paddingLeft: collapsed ? 0 : 8,
          }}
        >
          <Text
            strong
            style={{
              fontSize: collapsed ? 18 : 16,
              color: colorPrimary,
              fontWeight: 600,
              letterSpacing: collapsed ? 0 : "-0.3px",
            }}
          >
            {collapsed ? "MF" : "MediaFactory"}
          </Text>
        </div>

        {/* 分隔线 */}
        <div
          style={{
            height: 1,
            background: "#F3F4F6",
            margin: "0 16px 8px",
          }}
        />

        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{ border: "none" }}
        />

        {/* 折叠按钮 - 更精致 */}
        <Tooltip title={collapsed ? "展开" : "收起"} placement="right">
          <Button
            type="text"
            size="small"
            icon={collapsed ? <RightOutlined /> : <LeftOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{
              position: "absolute",
              right: -12,
              top: "50%",
              transform: "translateY(-50%)",
              width: 24,
              height: 24,
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              border: "1px solid #E5E7EB",
              background: "#FFFFFF",
              color: "#6B7280",
              fontSize: 10,
              boxShadow: "0 2px 4px rgba(0,0,0,0.06)",
              zIndex: 20,
            }}
          />
        </Tooltip>
      </Sider>
      <Layout
        style={{
          marginLeft: siderWidth,
          transition: "margin-left 0.2s ease",
        }}
      >
        <Content
          style={{
            margin: 20,
            padding: 24,
            minHeight: "calc(100vh - 40px)",
            background: colorBgContainer,
            borderRadius: borderRadiusLG,
            overflowY: "auto",
          }}
        >
          {children}
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
