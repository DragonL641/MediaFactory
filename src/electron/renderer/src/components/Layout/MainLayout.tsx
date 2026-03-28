/**
 * 主布局组件
 *
 * 包含侧边栏导航和主内容区域
 */

import React from "react";
import { Layout, Menu, Typography, theme, Select, Space } from "antd";
import {
  FileTextOutlined,
  CloudServerOutlined,
  CloudOutlined,
  SettingOutlined,
  GlobalOutlined,
} from "@ant-design/icons";
import { useNavigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useLanguage } from "../../hooks/useLanguage";

const { Sider, Content } = Layout;
const { Text } = Typography;

interface MainLayoutProps {
  children: React.ReactNode;
}

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();
  const { t } = useTranslation(["layout", "common"]);
  const { language, changeLanguage } = useLanguage();

  const menuItems = [
    {
      key: "/tasks",
      icon: <FileTextOutlined />,
      label: t("layout:menu.tasks"),
    },
    {
      key: "/models",
      icon: <CloudServerOutlined />,
      label: t("layout:menu.models"),
    },
    {
      key: "/llm-config",
      icon: <CloudOutlined />,
      label: t("layout:menu.llmConfig"),
    },
    {
      key: "/settings",
      icon: <SettingOutlined />,
      label: t("layout:menu.settings"),
    },
  ];

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
  };

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider
        width={200}
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
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Logo区域 */}
        <div
          style={{
            height: 56,
            margin: "12px 12px 8px",
            display: "flex",
            alignItems: "center",
            paddingLeft: 8,
          }}
        >
          <Text
            strong
            style={{
              fontSize: 16,
              color: "#2563EB",
              fontWeight: 600,
              letterSpacing: "-0.3px",
            }}
          >
            {t("layout:brand.full")}
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

        {/* 导航菜单 */}
        <div style={{ flex: 1 }}>
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            items={menuItems}
            onClick={handleMenuClick}
            style={{ border: "none" }}
          />
        </div>

        {/* 底部：语言切换器 */}
        <div
          style={{
            padding: "12px 16px",
            borderTop: "1px solid #F3F4F6",
          }}
        >
          <Space style={{ width: "100%" }} direction="vertical" size={4}>
            <Text
              type="secondary"
              style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 4 }}
            >
              <GlobalOutlined style={{ fontSize: 13 }} />
              {t("layout:language.label")}
            </Text>
            <Select
              value={language}
              onChange={(lang) => changeLanguage(lang)}
              size="small"
              style={{ width: "100%" }}
              options={[
                { value: "en", label: t("layout:language.en") },
                { value: "zh-CN", label: t("layout:language.zhCN") },
              ]}
            />
          </Space>
        </div>
      </Sider>
      <Layout
        style={{
          marginLeft: 200,
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
