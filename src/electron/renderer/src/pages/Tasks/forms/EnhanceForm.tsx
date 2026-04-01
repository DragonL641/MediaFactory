/**
 * 视频增强表单
 */

import React from "react";
import type { FormInstance } from "antd";
import { useTranslation } from "react-i18next";
import { useFileFilters } from "./shared";
import TaskFormWrapper from "./TaskFormWrapper";
import EnhanceFormFields from "./EnhanceFormFields";

interface EnhanceFormProps {
  form: FormInstance;
}

const EnhanceForm: React.FC<EnhanceFormProps> = ({ form }) => {
  const { t } = useTranslation("forms");
  const fileFilters = useFileFilters();

  return (
    <TaskFormWrapper
      form={form}
      initialValues={{
        scale: 4,
        model_type: "general",
        denoise: false,
        temporal: false,
      }}
      fileInput={{
        name: "video_path",
        label: t("forms:label.videoFile"),
        placeholder: t("forms:placeholder.selectVideo"),
        filters: fileFilters.video,
      }}
    >
      <EnhanceFormFields />
    </TaskFormWrapper>
  );
};

export default EnhanceForm;
