/**
 * 通用任务表单包装器
 *
 * 提取各任务表单的公共结构：Form + FileDialogInput + Fields
 */

import React from "react";
import { Form } from "antd";
import type { FormInstance } from "antd";
import FileDialogInput from "../../../components/Form/FileDialogInput";

interface TaskFormWrapperProps {
  form: FormInstance;
  initialValues: Record<string, unknown>;
  fileInput: {
    name: string;
    label: string;
    placeholder: string;
    filters: any;
  };
  children: React.ReactNode;
}

const TaskFormWrapper: React.FC<TaskFormWrapperProps> = ({
  form,
  initialValues,
  fileInput,
  children,
}) => (
  <Form form={form} layout="vertical" initialValues={initialValues}>
    <FileDialogInput
      form={form}
      name={fileInput.name}
      label={fileInput.label}
      placeholder={fileInput.placeholder}
      filters={fileInput.filters}
    />
    {children}
  </Form>
);

export default TaskFormWrapper;
