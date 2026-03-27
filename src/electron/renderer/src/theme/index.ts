/**
 * 应用主题配置
 *
 * 基于 Ant Design 5 Design Token 系统，统一管理颜色、间距、圆角等设计规范
 */

import type { ThemeConfig } from "antd";

export const appTheme: ThemeConfig = {
  token: {
    // 品牌色
    colorPrimary: "#1677ff",

    // 圆角
    borderRadius: 8,
    borderRadiusLG: 12,
    borderRadiusSM: 6,

    // 动画
    motionDurationSlow: "0.3s",
    motionDurationMid: "0.2s",
    motionDurationFast: "0.1s",
  },
  components: {
    Layout: {
      siderBg: "#ffffff",
      headerBg: "#ffffff",
      bodyBg: "#f6f8fa",
    },
    Menu: {
      itemBg: "transparent",
      itemSelectedBg: "rgba(22, 119, 255, 0.08)",
      itemSelectedColor: "#1677ff",
      itemHoverBg: "rgba(0, 0, 0, 0.04)",
    },
    Card: {
      paddingLG: 20,
    },
    Button: {
      primaryShadow: "0 1px 2px 0 rgba(22, 119, 255, 0.2)",
    },
  },
};
