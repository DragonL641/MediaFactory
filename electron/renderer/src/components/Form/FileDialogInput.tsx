/**
 * 文件选择输入框
 *
 * 封装文件对话框 + 只读输入框 + 选择按钮的通用模式
 */

import React from "react";
import { Form, Input, Button } from "antd";
import type { FormInstance } from "antd";
import { FolderOpenOutlined } from "@ant-design/icons";

export interface FileFilter {
  name: string;
  extensions: string[];
}

export interface FileDialogInputProps {
  form: FormInstance;
  name: string;
  label: string;
  placeholder?: string;
  filters: FileFilter[];
  required?: boolean;
  requiredMessage?: string;
}

const FileDialogInput: React.FC<FileDialogInputProps> = ({
  form,
  name,
  label,
  placeholder = "Click to select file...",
  filters,
  required = true,
  requiredMessage = "Please select a file",
}) => {
  const handleSelectFile = async () => {
    if (window.electronAPI) {
      const result = await window.electronAPI.openFileDialog({ filters });
      if (result && result.length > 0) {
        form.setFieldsValue({ [name]: result[0] });
      }
    }
  };

  return (
    <Form.Item
      name={name}
      label={label}
      rules={required ? [{ required, message: requiredMessage }] : undefined}
    >
      <Input
        readOnly
        placeholder={placeholder}
        suffix={
          <Button
            type="link"
            size="small"
            icon={<FolderOpenOutlined />}
            onClick={handleSelectFile}
          />
        }
      />
    </Form.Item>
  );
};

export default FileDialogInput;
