/**
 * 主布局组件
 *
 * 顶部 Tab Bar 导航 + 主内容区域
 * Soft Bento 设计风格
 */

import React from "react";
import { Layout, theme } from "antd";
import { FileTextOutlined, SettingOutlined, GlobalOutlined } from "@ant-design/icons";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useLanguage } from "../../hooks/useLanguage";
import TitleBar from "./TitleBar";
import { designTokens } from "../../theme";

const { Content } = Layout;

interface MainLayoutProps {
  children: React.ReactNode;
}

const TAB_ITEMS = [
  { key: "/tasks", icon: <FileTextOutlined /> },
  { key: "/settings", icon: <SettingOutlined /> },
];

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useTranslation("layout");
  const { language, changeLanguage } = useLanguage();

  // 确定 active tab
  const activeTab = location.pathname === "/settings" ? "/settings" : "/tasks";

  return (
    <Layout style={{ minHeight: "100vh", background: designTokens.colorBgLayout, display: "flex", flexDirection: "column" }}>
      {/* 顶部栏：Logo + 窗口控制 */}
      <TitleBar />

      {/* Tab 栏 */}
      <div className="tab-bar">
        <div className="tab-bar-tabs">
          {TAB_ITEMS.map((tab) => (
            <Link
              key={tab.key}
              to={tab.key}
              className={`tab-bar-tab ${activeTab === tab.key ? "tab-bar-tab-active" : ""}`}
            >
              {tab.icon}
              <span>{t(`tabs.${tab.key === "/tasks" ? "tasks" : "settings"}`)}</span>
            </Link>
          ))}
        </div>

        {/* 语言切换 */}
        <div
          className="lang-switcher"
          role="button"
          tabIndex={0}
          onClick={() => changeLanguage(language === "en" ? "zh-CN" : "en")}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              changeLanguage(language === "en" ? "zh-CN" : "en");
            }
          }}
        >
          <GlobalOutlined style={{ fontSize: 16 }} />
          <span>{language === "en" ? "EN" : "中"}</span>
        </div>
      </div>

      {/* 内容区域 */}
      <Content
        style={{
          padding: "24px 32px",
          flex: 1,
          overflowY: "auto",
        }}
      >
        {children}
      </Content>
    </Layout>
  );
};

export default MainLayout;
