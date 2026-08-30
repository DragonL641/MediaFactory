/**
 * 文件路径输入框
 *
 * 手动输入 + 服务端目录浏览（BrowseModal）双通道，替代 Electron 原生文件对话框
 */

import React, { useState } from "react";
import { Form, Input, Button, Tooltip } from "antd";
import type { FormInstance } from "antd";
import { FolderOpenOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import BrowseModal from "../BrowseModal";

export interface PathInputProps {
  form: FormInstance;
  name: string;
  label: string;
  placeholder?: string;
  /** 允许的文件扩展名（小写无点）；缺省不过滤 */
  extensions?: string[];
  required?: boolean;
  requiredMessage?: string;
}

const PathInput: React.FC<PathInputProps> = ({
  form,
  name,
  label,
  placeholder = "Enter or browse for a file...",
  extensions,
  required = true,
  requiredMessage = "Please select a file",
}) => {
  const { t } = useTranslation("forms");
  const [browseOpen, setBrowseOpen] = useState(false);

  return (
    <>
      <Form.Item
        name={name}
        label={label}
        rules={required ? [{ required, message: requiredMessage }] : undefined}
      >
        <Input
          placeholder={placeholder}
          allowClear
          suffix={
            <Tooltip title={t("pathInput.browse")}>
              <Button
                type="link"
                size="small"
                icon={<FolderOpenOutlined />}
                onClick={() => setBrowseOpen(true)}
              />
            </Tooltip>
          }
        />
      </Form.Item>
      <BrowseModal
        open={browseOpen}
        extensions={extensions}
        onCancel={() => setBrowseOpen(false)}
        onSelect={(path) => form.setFieldsValue({ [name]: path })}
      />
    </>
  );
};

export default PathInput;
