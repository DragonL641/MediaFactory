/**
 * 视频增强表单字段（不含 Form 包装和文件输入）
 * fieldPrefix 用于区分创建（无前缀）和编辑（"enhancement_" 前缀）的字段名
 */

import React from "react";
import { Form, Select, Switch } from "antd";
import { useTranslation } from "react-i18next";

interface EnhanceFormFieldsProps {
  fieldPrefix?: string;
}

const EnhanceFormFields: React.FC<EnhanceFormFieldsProps> = ({ fieldPrefix = "" }) => {
  const { t } = useTranslation("forms");

  return (
    <>
      <Form.Item name={`${fieldPrefix}scale`} label={t("forms:enhanceLabels.scale")}>
        <Select
          options={[
            { value: 2, label: "2x" },
            { value: 4, label: "4x" },
          ]}
        />
      </Form.Item>

      <Form.Item name={`${fieldPrefix}model_type`} label={t("forms:enhanceLabels.modelType")}>
        <Select
          options={[
            { value: "general", label: t("forms:enhanceLabels.general") },
            { value: "anime", label: t("forms:enhanceLabels.anime") },
          ]}
        />
      </Form.Item>

      <Form.Item name={`${fieldPrefix}denoise`} label={t("forms:enhanceLabels.enableDenoising")} valuePropName="checked">
        <Switch />
      </Form.Item>

      <Form.Item name={`${fieldPrefix}temporal`} label={t("forms:enhanceLabels.enableTemporalSmoothing")} valuePropName="checked">
        <Switch />
      </Form.Item>
    </>
  );
};

export default EnhanceFormFields;
