/**
 * 任务表单共享常量与 hooks
 */

import { useTranslation } from "react-i18next";

// 源语言选项（包含 auto detect）
export const useLanguageOptions = () => {
  const { t } = useTranslation("forms");
  return [
    { value: "auto", label: t("forms:language.autoDetect") },
    ...useTargetLanguageOptions(),
  ];
};

// 目标语言选项（不含 auto detect）
export const useTargetLanguageOptions = () => {
  const { t } = useTranslation("forms");
  return [
    { value: "en", label: t("forms:language.english") },
    { value: "zh", label: t("forms:language.chinese") },
    { value: "ja", label: t("forms:language.japanese") },
    { value: "ko", label: t("forms:language.korean") },
    { value: "fr", label: t("forms:language.french") },
    { value: "de", label: t("forms:language.german") },
    { value: "es", label: t("forms:language.spanish") },
    { value: "ru", label: t("forms:language.russian") },
    { value: "ar", label: t("forms:language.arabic") },
    { value: "hi", label: t("forms:language.hindi") },
    { value: "it", label: t("forms:language.italian") },
    { value: "pt", label: t("forms:language.portuguese") },
    { value: "nl", label: t("forms:language.dutch") },
  ];
};

export const useOutputFormatOptions = () => {
  const { t } = useTranslation("forms");
  return [
    { value: "srt", label: t("forms:outputFormat.srt") },
    { value: "ass", label: t("forms:outputFormat.ass") },
    { value: "txt", label: t("forms:outputFormat.txt") },
  ];
};

export const useStylePresetOptions = () => {
  const { t } = useTranslation("forms");
  return [
    { value: "default", label: t("forms:stylePreset.default") },
    { value: "science", label: t("forms:stylePreset.science") },
    { value: "anime", label: t("forms:stylePreset.anime") },
    { value: "news", label: t("forms:stylePreset.news") },
  ];
};

export const useBilingualLayoutOptions = () => {
  const { t } = useTranslation("forms");
  return [
    { value: "translate_on_top", label: t("forms:bilingualLayout.translateOnTop") },
    { value: "original_on_top", label: t("forms:bilingualLayout.originalOnTop") },
    { value: "translate_only", label: t("forms:bilingualLayout.translateOnly") },
    { value: "original_only", label: t("forms:bilingualLayout.originalOnly") },
  ];
};

export const useFileFilters = () => {
  const { t } = useTranslation("forms");
  return {
    video: [{ name: t("forms:fileFilter.video"), extensions: ["mp4", "avi", "mov", "mkv", "wmv", "flv", "webm"] }],
    audio_video: [{ name: t("forms:fileFilter.audioVideo"), extensions: ["mp4", "avi", "mov", "mkv", "wav", "mp3", "m4a", "flac", "webm", "ogg"] }],
    srt: [{ name: t("forms:fileFilter.srt"), extensions: ["srt"] }],
  };
};
