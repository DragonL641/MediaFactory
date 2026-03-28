/**
 * 视频增强表单
 */

import React from "react";
import { Form, Select, Switch } from "antd";
import type { FormInstance } from "antd";
import { useTranslation } from "react-i18next";
import { useFileFilters } from "./shared";
import FileDialogInput from "../../../components/Form/FileDialogInput";

interface EnhanceFormProps {
  form: FormInstance;
}

const EnhanceForm: React.FC<EnhanceFormProps> = ({ form }) => {
  const { t } = useTranslation("forms");
  const fileFilters = useFileFilters();

  return (
    <Form form={form} layout="vertical" initialValues={{
      scale: 4,
      model_type: "general",
      denoise: false,
      temporal: false,
    }}>
      <FileDialogInput
        form={form}
        name="video_path"
        label={t("forms:label.videoFile")}
        placeholder={t("forms:placeholder.selectVideo")}
        filters={fileFilters.video}
      />

      <Form.Item name="scale" label={t("forms:enhanceLabels.scale")}>
        <Select
          options={[
            { value: 2, label: "2x" },
            { value: 4, label: "4x" },
          ]}
        />
      </Form.Item>

      <Form.Item name="model_type" label={t("forms:enhanceLabels.modelType")}>
        <Select
          options={[
            { value: "general", label: t("forms:enhanceLabels.general") },
            { value: "anime", label: t("forms:enhanceLabels.anime") },
          ]}
        />
      </Form.Item>

      <Form.Item name="denoise" label={t("forms:enhanceLabels.enableDenoising")} valuePropName="checked">
        <Switch />
      </Form.Item>

      <Form.Item name="temporal" label={t("forms:enhanceLabels.enableTemporalSmoothing")} valuePropName="checked">
        <Switch />
      </Form.Item>
    </Form>
  );
};

export default EnhanceForm;
