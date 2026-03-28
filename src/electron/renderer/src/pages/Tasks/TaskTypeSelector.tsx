/**
 * 任务类型选择器
 *
 * Step 1：选择任务类型（5种）
 */

import React from "react";
import { Card, Row, Col, Typography, theme } from "antd";
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
      key: "subtitle",
      title: t("tasks:typeOptions.subtitle.title"),
      description: t("tasks:typeOptions.subtitle.description"),
      icon: <SoundOutlined style={{ fontSize: 32 }} />,
    },
    {
      key: "audio",
      title: t("tasks:typeOptions.audio.title"),
      description: t("tasks:typeOptions.audio.description"),
      icon: <AudioOutlined style={{ fontSize: 32 }} />,
    },
    {
      key: "transcribe",
      title: t("tasks:typeOptions.transcribe.title"),
      description: t("tasks:typeOptions.transcribe.description"),
      icon: <SoundOutlined style={{ fontSize: 32 }} />,
    },
    {
      key: "translate",
      title: t("tasks:typeOptions.translate.title"),
      description: t("tasks:typeOptions.translate.description"),
      icon: <TranslationOutlined style={{ fontSize: 32 }} />,
    },
    {
      key: "enhance",
      title: t("tasks:typeOptions.enhance.title"),
      description: t("tasks:typeOptions.enhance.description"),
      icon: <VideoCameraOutlined style={{ fontSize: 32 }} />,
    },
  ];
};

interface TaskTypeSelectorProps {
  onSelect: (typeKey: string) => void;
}

const TaskTypeSelector: React.FC<TaskTypeSelectorProps> = ({ onSelect }) => {
  const { token } = theme.useToken();
  const taskTypes = useTaskTypes();

  return (
    <Row gutter={[16, 16]} justify="center">
      {taskTypes.map((type) => (
        <Col xs={24} sm={12} md={8} key={type.key}>
          <Card
            hoverable
            onClick={() => onSelect(type.key)}
            style={{ textAlign: "center", height: 140 }}
            styles={{
              body: {
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
              },
            }}
          >
            <div style={{ marginBottom: 12, color: token.colorPrimary }}>{type.icon}</div>
            <Text strong>{type.title}</Text>
            <br />
            <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
              {type.description}
            </Text>
          </Card>
        </Col>
      ))}
    </Row>
  );
};

export default TaskTypeSelector;
