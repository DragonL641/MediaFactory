/**
 * 应用主题配置
 *
 * 基于 Ant Design 5 Design Token 系统，统一管理颜色、间距、圆角等设计规范
 * UI风格：简洁高级、颜色协调、重点突出
 */

import type { ThemeConfig } from "antd";

// 设计 Token 常量 - 便于全局复用
export const designTokens = {
  // 品牌色系 - 偏冷蓝，更高级
  colorPrimary: "#2563EB",
  colorPrimaryHover: "#3B82F6",
  colorPrimaryActive: "#1D4ED8",

  // 语义色 - 柔和不刺眼
  colorSuccess: "#16A34A",
  colorWarning: "#EA580C",
  colorError: "#DC2626",
  colorInfo: "#0EA5E9",

  // 文字色阶
  colorTextHeading: "#111827",
  colorText: "#374151",
  colorTextSecondary: "#6B7280",
  colorTextTertiary: "#9CA3AF",
  colorTextQuaternary: "#D1D5DB",

  // 背景色
  colorBgLayout: "#F8FAFC",
  colorBgContainer: "#FFFFFF",
  colorBgElevated: "#FFFFFF",
  colorBgSpotlight: "#F1F5F9",

  // 边框
  colorBorder: "#E5E7EB",
  colorBorderSecondary: "#F3F4F6",

  // 圆角
  borderRadius: 8,
  borderRadiusLG: 12,
  borderRadiusSM: 6,
  borderRadiusXS: 4,

  // 间距
  padding: 16,
  paddingLG: 24,
  paddingSM: 12,
  paddingXS: 8,

  // 阴影 - 更轻更柔和
  boxShadow:
    "0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05)",
  boxShadowSecondary:
    "0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.05)",
};

export const appTheme: ThemeConfig = {
  token: {
    colorPrimary: designTokens.colorPrimary,
    colorSuccess: designTokens.colorSuccess,
    colorWarning: designTokens.colorWarning,
    colorError: designTokens.colorError,
    colorInfo: designTokens.colorInfo,

    colorText: designTokens.colorText,
    colorTextSecondary: designTokens.colorTextSecondary,
    colorTextTertiary: designTokens.colorTextTertiary,
    colorTextQuaternary: designTokens.colorTextQuaternary,

    colorBgLayout: designTokens.colorBgLayout,
    colorBgContainer: designTokens.colorBgContainer,
    colorBgElevated: designTokens.colorBgElevated,
    colorBgSpotlight: designTokens.colorBgSpotlight,

    colorBorder: designTokens.colorBorder,
    colorBorderSecondary: designTokens.colorBorderSecondary,

    borderRadius: designTokens.borderRadius,
    borderRadiusLG: designTokens.borderRadiusLG,
    borderRadiusSM: designTokens.borderRadiusSM,

    boxShadow: designTokens.boxShadow,
    boxShadowSecondary: designTokens.boxShadowSecondary,

    fontFamily:
      '-apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, "Helvetica Neue", sans-serif',

    motionDurationSlow: "0.3s",
    motionDurationMid: "0.2s",
    motionDurationFast: "0.1s",
  },
  components: {
    Layout: {
      siderBg: "#FFFFFF",
      headerBg: "#FFFFFF",
      bodyBg: designTokens.colorBgLayout,
    },
    Menu: {
      itemBg: "transparent",
      itemSelectedBg: `${designTokens.colorPrimary}08`,
      itemSelectedColor: designTokens.colorPrimary,
      itemHoverBg: "rgba(0, 0, 0, 0.03)",
      itemMarginInline: 8,
      itemBorderRadius: 8,
    },
    Card: {
      paddingLG: 20,
      borderRadiusLG: 12,
      boxShadowTertiary: designTokens.boxShadow,
    },
    Button: {
      primaryShadow: "0 1px 2px 0 rgba(37, 99, 235, 0.2)",
      defaultBorderColor: designTokens.colorBorder,
      borderRadius: 8,
      controlHeight: 36,
      controlHeightSM: 28,
      controlHeightLG: 44,
    },
    Tag: {
      borderRadiusSM: 6,
    },
    Input: {
      borderRadius: 8,
      controlHeight: 36,
    },
    InputNumber: {
      borderRadius: 8,
      controlHeight: 36,
    },
    Switch: {
      colorPrimary: designTokens.colorPrimary,
    },
    Empty: {
      colorTextDescription: designTokens.colorTextTertiary,
    },
  },
};
