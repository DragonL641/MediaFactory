/**
 * 术语表文件上传字段（可选）：读取 JSON 内容并校验后写入表单。
 * 提交时 terminology 作为普通表单值随任务一起发送。
 *
 * 注意：值承载在 hidden 的 Form.Item（name="terminology"）上；
 * Upload 的 Form.Item 不带 name——否则 rc-upload 的 onChange 会把
 * {file, fileList} 事件对象覆盖进表单值（评审 Critical 2）。
 */

import React from "react";
import { App, Button, Form, Input, Upload } from "antd";
import { UploadOutlined } from "@ant-design/icons";
import type { FormInstance } from "antd";
import { useTranslation } from "react-i18next";

interface TerminologyFileFieldProps {
  form: FormInstance;
}

const MAX_ENTRIES = 200;
const MAX_VALUE_LENGTH = 200;

const TerminologyFileField: React.FC<TerminologyFileFieldProps> = ({ form }) => {
  const { message } = App.useApp();
  const { t } = useTranslation("forms");

  const parseFile = async (file: File) => {
    try {
      const data = JSON.parse(await file.text());
      if (typeof data !== "object" || data === null || Array.isArray(data)) {
        throw new Error("not an object");
      }
      const entries = Object.entries(data);
      if (entries.length > MAX_ENTRIES) {
        throw new Error("too many entries");
      }
      const invalid = entries.some(
        ([k, v]) =>
          typeof k !== "string" ||
          typeof v !== "string" ||
          k.length > MAX_VALUE_LENGTH ||
          v.length > MAX_VALUE_LENGTH,
      );
      if (invalid) {
        throw new Error("invalid entries");
      }
      form.setFieldValue("terminology", Object.fromEntries(entries));
      message.success(
        t("forms:label.terminologyLoaded", { count: entries.length }),
      );
    } catch {
      message.error(t("forms:label.terminologyInvalid"));
    }
    return false; // 阻止 antd 自动上传
  };

  return (
    <>
      {/* 值承载字段：hidden，避免 Upload onChange 覆盖 */}
      <Form.Item name="terminology" hidden>
        <Input type="hidden" />
      </Form.Item>
      <Form.Item
        label={t("forms:label.terminologyFile")}
        tooltip={t("forms:label.terminologyTooltip")}
      >
        <Upload
          maxCount={1}
          accept=".json"
          showUploadList={false}
          beforeUpload={parseFile}
        >
          <Button icon={<UploadOutlined />}>
            {t("forms:label.chooseTerminologyFile")}
          </Button>
        </Upload>
      </Form.Item>
    </>
  );
};

export default TerminologyFileField;
