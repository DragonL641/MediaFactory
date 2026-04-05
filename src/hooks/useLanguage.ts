/**
 * 语言切换 Hook
 *
 * 切换 i18next 语言并同步到后端 config.toml
 */

import { useCallback } from "react";
import { useTranslation } from "react-i18next";
import { getApiClient } from "../api/client";

export function useLanguage() {
  const { i18n } = useTranslation();

  const changeLanguage = useCallback(
    async (lang: string) => {
      // 1. 切换前端语言
      await i18n.changeLanguage(lang);

      // 2. 同步到后端 config.toml
      try {
        const client = getApiClient();
        await client.put("/api/config/", {
          app: { language: lang },
        });
        await client.post("/api/config/save");
      } catch (e) {
        console.error("Failed to sync language to backend:", e);
      }
    },
    [i18n]
  );

  return {
    language: i18n.language,
    changeLanguage,
  };
}
