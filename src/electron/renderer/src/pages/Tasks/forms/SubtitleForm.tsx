/**
 * 字幕生成表单
 */

import React from "react";
import type { FormInstance } from "antd";
import { useTranslation } from "react-i18next";
import { useFileFilters } from "./shared";
import TaskFormWrapper from "./TaskFormWrapper";
import SubtitleFormFields from "./SubtitleFormFields";

interface SubtitleFormProps {
  form: FormInstance;
  llmAvailable?: boolean;
}

const SubtitleForm: React.FC<SubtitleFormProps> = ({ form, llmAvailable = true }) => {
  const { t } = useTranslation("forms");
  const fileFilters = useFileFilters();

  return (
    <TaskFormWrapper
      form={form}
      initialValues={{
        source_lang: "auto",
        target_lang: "zh",
        output_format: "srt",
        style_preset: "default",
        bilingual: false,
        bilingual_layout: "translate_on_top",
        use_llm: false,
      }}
      fileInput={{
        name: "video_path",
        label: t("forms:label.videoFile"),
        placeholder: t("forms:placeholder.selectVideo"),
        filters: fileFilters.video,
      }}
    >
      <SubtitleFormFields form={form} llmAvailable={llmAvailable} />
    </TaskFormWrapper>
  );
};

export default SubtitleForm;
