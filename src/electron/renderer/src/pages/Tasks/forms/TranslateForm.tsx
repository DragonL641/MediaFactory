/**
 * 字幕翻译表单
 */

import React from "react";
import type { FormInstance } from "antd";
import { useTranslation } from "react-i18next";
import { useFileFilters } from "./shared";
import TaskFormWrapper from "./TaskFormWrapper";
import TranslateFormFields from "./TranslateFormFields";

interface TranslateFormProps {
  form: FormInstance;
}

const TranslateForm: React.FC<TranslateFormProps> = ({ form }) => {
  const { t } = useTranslation("forms");
  const fileFilters = useFileFilters();

  return (
    <TaskFormWrapper
      form={form}
      initialValues={{
        source_lang: "auto",
        target_lang: "zh",
        use_llm: false,
      }}
      fileInput={{
        name: "srt_path",
        label: t("forms:label.srtFile"),
        placeholder: t("forms:placeholder.selectSrt"),
        filters: fileFilters.srt,
      }}
    >
      <TranslateFormFields form={form} />
    </TaskFormWrapper>
  );
};

export default TranslateForm;
