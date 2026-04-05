/**
 * LLM Provider 选择器
 *
 * 带连接状态指示的 LLM 预设下拉选择
 */

import React from "react";
import { Form, Select, theme } from "antd";
import type { FormInstance } from "antd";
import { useTranslation } from "react-i18next";
import type { LLMPresetInfo } from "../../types";
import { useLLMPresetsQuery } from "../../api/queries";

export interface LLMProviderSelectProps {
  form: FormInstance;
  name?: string;
  label?: string;
  required?: boolean;
  placeholder?: string;
  configuredPresets?: string[];
}

const LLMProviderSelect: React.FC<LLMProviderSelectProps> = ({
  form,
  name = "llm_preset",
  label,
  required = true,
  placeholder,
  configuredPresets,
}) => {
  const { t } = useTranslation("forms");
  const { token } = theme.useToken();
  const resolvedLabel = label ?? t("forms:label.llmProvider");
  const resolvedPlaceholder = placeholder ?? t("forms:placeholder.selectProvider");
  const { data: presetsData } = useLLMPresetsQuery();

  const presetOptions = presetsData
    ? (Object.entries(presetsData) as [string, LLMPresetInfo][])
        .filter(([id]) => !configuredPresets || configuredPresets.includes(id))
        .map(([id, info]) => ({
        value: id,
        label: info.display_name,
        connected: info.connection_available,
      }))
    : [];

  return (
    <Form.Item name={name} label={resolvedLabel} rules={required ? [{ required }] : undefined}>
      <Select
        placeholder={resolvedPlaceholder}
        options={presetOptions.map((p) => ({
          value: p.value,
          label: (
            <span>
              {p.label}{" "}
              {p.connected !== undefined && (
                <span
                  style={{
                    color: p.connected ? token.colorSuccess : token.colorTextTertiary,
                    fontSize: token.fontSizeSM,
                  }}
                >
                  {p.connected ? t("llmConfig:card.connected") : ""}
                </span>
              )}
            </span>
          ),
        }))}
      />
    </Form.Item>
  );
};

export default LLMProviderSelect;
