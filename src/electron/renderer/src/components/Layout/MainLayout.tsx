/**
 * 主布局组件
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

  const siderWidth = collapsed ? 80 : 200;

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider
        width={200}
        collapsedWidth={80}
        collapsed={collapsed}
        trigger={null}
        style={{
          overflow: "auto",
          height: "100vh",
          position: "fixed",
          left: 0,
          top: 0,
          bottom: 0,
          borderRight: `1px solid ${colorPrimary}10`,
          zIndex: 10,
          transition: "width 0.2s",
        }}
      >
        <div
          style={{
            height: 48,
            margin: "16px 16px 8px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            borderRadius: 8,
            background: `${colorPrimary}08`,
          }}
        >
          <Text
            strong
            style={{ fontSize: collapsed ? 16 : 15, color: colorPrimary }}
          >
            {collapsed ? "MF" : "MediaFactory"}
          </Text>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
        />
        {/* 自定义折叠按钮：侧边栏右边线中部 */}
        <Tooltip title={collapsed ? "Expand" : "Collapse"} placement="right">
          <Button
            type="text"
            size="small"
            icon={collapsed ? <RightOutlined /> : <LeftOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{
              position: "absolute",
              right: -14,
              top: "50%",
              transform: "translateY(-50%)",
              width: 28,
              height: 28,
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              border: `1px solid ${colorPrimary}30`,
              background: colorBgElevated,
              color: colorPrimary,
              fontSize: 10,
              boxShadow: "0 1px 4px rgba(0,0,0,0.1)",
              zIndex: 20,
            }}
          />
        </Tooltip>
      </Sider>
      <Layout
        style={{
          marginLeft: siderWidth,
          transition: "margin-left 0.2s",
        }}
      >
        <Content
          style={{
            margin: 24,
            padding: 24,
            minHeight: "calc(100vh - 48px)",
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
