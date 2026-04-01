/**
 * 任务类型选择器
 *
 * Step 1：选择任务类型（5种）
 * Soft Bento 风格：圆角选项卡片，hover 变色
 */

import React from "react";
import { Typography } from "antd";
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
}

export const useTaskTypes = (): TaskTypeOption[] => {
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
    },
    {
      key: "translate",
      title: t("typeOptions.translate.title"),
      description: t("typeOptions.translate.description"),
      icon: <TranslationOutlined style={{ fontSize: 20 }} />,
    },
    {
      key: "subtitle",
      title: t("typeOptions.subtitle.title"),
      description: t("typeOptions.subtitle.description"),
      icon: <SoundOutlined style={{ fontSize: 20 }} />,
    },
    {
      key: "enhance",
      title: t("typeOptions.enhance.title"),
      description: t("typeOptions.enhance.description"),
      icon: <VideoCameraOutlined style={{ fontSize: 20 }} />,
    },
  ];
};

interface TaskTypeSelectorProps {
  onSelect: (typeKey: string) => void;
}

const TaskTypeSelector: React.FC<TaskTypeSelectorProps> = ({ onSelect }) => {
  const taskTypes = useTaskTypes();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {taskTypes.map((type) => (
        <div
          key={type.key}
          role="button"
          tabIndex={0}
          onClick={() => onSelect(type.key)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
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
            cursor: "pointer",
            transition: "all 0.2s",
            background: "var(--mf-surface-secondary, #FFFFFF)",
          }}
        >
          <div style={{
            color: "var(--mf-primary, #8F5A3C)",
            display: "flex",
            alignItems: "center",
            width: 36,
            height: 36,
            borderRadius: 8,
            background: "var(--mf-primary-bg, #FDF8F5)",
            justifyContent: "center",
          }}>
            {type.icon}
          </div>
          <div style={{ flex: 1 }}>
            <Text strong style={{ fontSize: 14 }}>{type.title}</Text>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {type.description}
            </Text>
          </div>
        </div>
      ))}
    </div>
  );
};

export default TaskTypeSelector;
