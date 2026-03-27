/**
 * LLM Provider 选择器
 *
 * 带连接状态指示的 LLM 预设下拉选择
 */

import React from "react";
import { Form, Select, theme } from "antd";
import type { FormInstance } from "antd";
import type { LLMPresetInfo } from "../../types";
import { useLLMPresetsQuery } from "../../api/queries";

export interface LLMProviderSelectProps {
  form: FormInstance;
  name?: string;
  label?: string;
  required?: boolean;
  placeholder?: string;
}

const LLMProviderSelect: React.FC<LLMProviderSelectProps> = ({
  form,
  name = "llm_preset",
  label = "LLM Provider",
  required = true,
  placeholder = "Select provider",
}) => {
  const { token } = theme.useToken();
  const { data: presetsData } = useLLMPresetsQuery();

  const presetOptions = presetsData
    ? (Object.entries(presetsData) as [string, LLMPresetInfo][]).map(([id, info]) => ({
        value: id,
        label: info.display_name,
        connected: info.connection_available,
      }))
    : [];

  return (
    <Form.Item name={name} label={label} rules={required ? [{ required }] : undefined}>
      <Select
        placeholder={placeholder}
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
                  {p.connected ? "(Connected)" : ""}
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
