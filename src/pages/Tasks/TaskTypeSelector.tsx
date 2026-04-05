/**
 * 任务类型选择器
 *
 * Step 1：选择任务类型（5种）
 * 支持根据模型就绪状态禁用不可用的类型
 */

import React from "react";
import { Typography, Tooltip } from "antd";
import {
  AudioOutlined,
  SoundOutlined,
  TranslationOutlined,
  VideoCameraOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";

const { Text } = Typography;

export interface TaskTypeOption {
  key: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  disabled?: boolean;
  disabledReason?: string;
}

export const useTaskTypes = (disabledTypes?: Record<string, { disabled: boolean; reason?: string }>): TaskTypeOption[] => {
  const { t } = useTranslation("tasks");
  return [
    {
      key: "audio",
      title: t("typeOptions.audio.title"),
      description: t("typeOptions.audio.description"),
      icon: <AudioOutlined style={{ fontSize: 20 }} />,
    },
    {
      key: "transcribe",
      title: t("typeOptions.transcribe.title"),
      description: t("typeOptions.transcribe.description"),
      icon: <SoundOutlined style={{ fontSize: 20 }} />,
      disabled: disabledTypes?.["transcribe"]?.disabled,
      disabledReason: disabledTypes?.["transcribe"]?.reason,
    },
    {
      key: "translate",
      title: t("typeOptions.translate.title"),
      description: t("typeOptions.translate.description"),
      icon: <TranslationOutlined style={{ fontSize: 20 }} />,
      disabled: disabledTypes?.["translate"]?.disabled,
      disabledReason: disabledTypes?.["translate"]?.reason,
    },
    {
      key: "subtitle",
      title: t("typeOptions.subtitle.title"),
      description: t("typeOptions.subtitle.description"),
      icon: <SoundOutlined style={{ fontSize: 20 }} />,
      disabled: disabledTypes?.["subtitle"]?.disabled,
      disabledReason: disabledTypes?.["subtitle"]?.reason,
    },
    {
      key: "enhance",
      title: t("typeOptions.enhance.title"),
      description: t("typeOptions.enhance.description"),
      icon: <VideoCameraOutlined style={{ fontSize: 20 }} />,
      disabled: disabledTypes?.["enhance"]?.disabled,
      disabledReason: disabledTypes?.["enhance"]?.reason,
    },
  ];
};

interface TaskTypeSelectorProps {
  onSelect: (typeKey: string) => void;
  disabledTypes?: Record<string, { disabled: boolean; reason?: string }>;
}

const TaskTypeSelector: React.FC<TaskTypeSelectorProps> = ({ onSelect, disabledTypes }) => {
  const taskTypes = useTaskTypes(disabledTypes);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {taskTypes.map((type) => {
        const isDisabled = type.disabled;

        const content = (
          <div
            key={type.key}
            role="button"
            tabIndex={isDisabled ? -1 : 0}
            onClick={() => !isDisabled && onSelect(type.key)}
            onKeyDown={(e) => {
              if (!isDisabled && (e.key === "Enter" || e.key === " ")) {
                e.preventDefault();
                onSelect(type.key);
              }
            }}
            className="task-type-option"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 16,
              padding: "12px 16px",
              borderRadius: 10,
              border: "1px solid var(--mf-border, #E5E2DD)",
              cursor: isDisabled ? "not-allowed" : "pointer",
              transition: "all 0.2s",
              background: "var(--mf-surface-secondary, #FFFFFF)",
              opacity: isDisabled ? 0.5 : 1,
            }}
          >
            <div style={{
              color: isDisabled
                ? "var(--mf-text-muted, #999)"
                : "var(--mf-primary, #8F5A3C)",
              display: "flex",
              alignItems: "center",
              width: 36,
              height: 36,
              borderRadius: 8,
              background: isDisabled
                ? "var(--mf-surface-tertiary, #F5F5F5)"
                : "var(--mf-primary-bg, #FDF8F5)",
              justifyContent: "center",
            }}>
              {type.icon}
            </div>
            <div style={{ flex: 1 }}>
              <Text strong style={{ fontSize: 14, color: isDisabled ? "var(--mf-text-muted, #999)" : undefined }}>
                {type.title}
              </Text>
              <br />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {isDisabled && type.disabledReason ? type.disabledReason : type.description}
              </Text>
            </div>
          </div>
        );

        return isDisabled && type.disabledReason ? (
          <Tooltip key={type.key} title={type.disabledReason}>
            {content}
          </Tooltip>
        ) : (
          <React.Fragment key={type.key}>{content}</React.Fragment>
        );
      })}
    </div>
  );
};

export default TaskTypeSelector;
