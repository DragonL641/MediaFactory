/**
 * 应用主题配置 — Soft Bento 设计系统
 *
 * 暖色混凝土色系，圆角卡片，清晰层次
 * 基于 Ant Design 5 Design Token 系统
 */

import type { ThemeConfig } from "antd";

// Soft Bento 设计 Token
export const designTokens = {
  // 品牌色 - 温暖棕色
  colorPrimary: "#8F5A3C",
  colorPrimaryHover: "#A06B4D",
  colorPrimaryActive: "#7D4E33",
  colorPrimaryBg: "#FDF8F5",

  // 功能色
  colorSuccess: "#16A34A",
  colorSuccessBg: "#F0FDF4",
  colorWarning: "#EA580C",
  colorWarningBg: "#FFF7ED",
  colorError: "#DC2626",
  colorErrorBg: "#FEF2F2",
  colorInfo: "#2563EB",
  colorInfoBg: "#EFF6FF",

  // 文字色阶
  colorTextHeading: "#1A1A1A",
  colorText: "#1A1A1A",
  colorTextSecondary: "#666666",
  colorTextTertiary: "#999999",
  colorTextQuaternary: "#CCCCCC",

  // 表面色
  colorBgLayout: "#F5F3F0",
  colorBgContainer: "#FFFFFF",
  colorBgElevated: "#FFFFFF",
  colorBgSpotlight: "#EEECEA",
  colorBgInverse: "#1A1A1A",
  colorTextInverse: "#FFFFFF",

  // 边框色
  colorBorder: "#E5E2DD",
  colorBorderSecondary: "#EEECEA",

  // 圆角
  borderRadius: 8,
  borderRadiusLG: 16,
  borderRadiusSM: 6,
  borderRadiusXS: 4,

  // 间距
  padding: 16,
  paddingLG: 24,
  paddingSM: 12,
  paddingXS: 8,

  // 阴影 - 柔和
  boxShadow: "0 1px 2px 0 rgba(0, 0, 0, 0.04)",
  boxShadowSecondary: "0 4px 6px -1px rgba(0, 0, 0, 0.06)",
  boxShadowCard: "0 1px 2px 0 rgba(0, 0, 0, 0.04)",
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
      '"Inter", -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, "Helvetica Neue", sans-serif',
    fontFamilyCode: '"Geist Mono", "SF Mono", "Fira Code", monospace',

    motionDurationSlow: "0.3s",
    motionDurationMid: "0.2s",
    motionDurationFast: "0.1s",

    fontSize: 14,
    fontSizeHeading1: 24,
    fontSizeHeading2: 20,
    fontSizeHeading3: 16,
    lineHeight: 1.5,
  },
  components: {
    Layout: {
      headerBg: designTokens.colorBgInverse,
      bodyBg: designTokens.colorBgLayout,
    },
    Card: {
      paddingLG: 20,
      borderRadiusLG: 16,
      boxShadowTertiary: designTokens.boxShadowCard,
    },
    Button: {
      primaryShadow: "0 1px 2px 0 rgba(143, 90, 60, 0.2)",
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
    Select: {
      borderRadius: 8,
      controlHeight: 36,
    },
    Tooltip: {
      colorBgSpotlight: "#1A1A1A",
    },
    Empty: {
      colorTextDescription: designTokens.colorTextTertiary,
    },
    Modal: {
      borderRadiusLG: 16,
    },
    Progress: {
      remainingColor: designTokens.colorBorderSecondary,
    },
    Tabs: {
      horizontalItemPadding: "6px 16px",
      horizontalItemPaddingLG: "6px 16px",
      inkBarColor: designTokens.colorPrimary,
      itemSelectedColor: designTokens.colorText,
      itemColor: designTokens.colorTextSecondary,
    },
  },
};
