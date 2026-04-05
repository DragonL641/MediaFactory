/**
 * i18n 初始化
 *
 * 使用 react-i18next，翻译文件由 Vite bundle 到渲染进程
 */

import i18n from "i18next";
import { initReactI18next } from "react-i18next";

// 英文翻译
import enCommon from "../locales/en/common.json";
import enLayout from "../locales/en/layout.json";
import enTasks from "../locales/en/tasks.json";
import enModels from "../locales/en/models.json";
import enLLMConfig from "../locales/en/llmConfig.json";
import enSettings from "../locales/en/settings.json";
import enForms from "../locales/en/forms.json";

// 中文翻译
import zhCNCommon from "../locales/zh-CN/common.json";
import zhCNLayout from "../locales/zh-CN/layout.json";
import zhCNTasks from "../locales/zh-CN/tasks.json";
import zhCNModels from "../locales/zh-CN/models.json";
import zhCNLLMConfig from "../locales/zh-CN/llmConfig.json";
import zhCNSettings from "../locales/zh-CN/settings.json";
import zhCNForms from "../locales/zh-CN/forms.json";

const resources = {
  en: {
    common: enCommon,
    layout: enLayout,
    tasks: enTasks,
    models: enModels,
    llmConfig: enLLMConfig,
    settings: enSettings,
    forms: enForms,
  },
  "zh-CN": {
    common: zhCNCommon,
    layout: zhCNLayout,
    tasks: zhCNTasks,
    models: zhCNModels,
    llmConfig: zhCNLLMConfig,
    settings: zhCNSettings,
    forms: zhCNForms,
  },
};

i18n.use(initReactI18next).init({
  resources,
  lng: "en",
  fallbackLng: "en",
  interpolation: {
    escapeValue: false,
  },
  ns: ["common", "layout", "tasks", "models", "llmConfig", "settings", "forms"],
  defaultNS: "common",
});

export default i18n;
