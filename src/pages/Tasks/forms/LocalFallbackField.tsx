/**
 * 本地兜底开关 + 兜底模型选择。
 *
 * Switch 可打开条件：Ollama 可用且有已装模型，且主渠道不是 ollama preset
 * （单向约束：本地主渠道不兜底）。fallback_model 设 preserve=false，
 * 开关关闭时值随之清除。enable_local_fallback 仅为 UI 字段，不提交。
 */

import React from "react";
import { Form, Select, Switch } from "antd";
import type { FormInstance } from "antd";
import { useTranslation } from "react-i18next";
import { useLocalModelsQuery } from "../../../api/queries";

interface LocalFallbackFieldProps {
  form: FormInstance;
}

const LocalFallbackField: React.FC<LocalFallbackFieldProps> = ({ form }) => {
  const { t } = useTranslation("forms");
  const { data: local } = useLocalModelsQuery();
  const enableFallback = Form.useWatch("enable_local_fallback", form);
  const presetId = Form.useWatch("llm_preset", form);

  const localReady = !!local?.available && (local?.models?.length ?? 0) > 0;
  const primaryIsLocal = presetId === "ollama";
  const switchDisabled = !localReady || primaryIsLocal;

  return (
    <>
      <Form.Item
        name="enable_local_fallback"
        label={t("forms:label.localFallback")}
        valuePropName="checked"
      >
        <Switch disabled={switchDisabled} />
      </Form.Item>

      {enableFallback && !switchDisabled && (
        <Form.Item
          name="fallback_model"
          label={t("forms:label.fallbackModel")}
          preserve={false}
          rules={[
            { required: true, message: t("forms:validation.fallbackModelRequired") },
          ]}
        >
          <Select
            showSearch
            placeholder={t("forms:placeholder.selectFallbackModel")}
            options={(local?.models ?? []).map((m) => ({
              value: m.name,
              label: m.name,
            }))}
          />
        </Form.Item>
      )}
    </>
  );
};

export default LocalFallbackField;
