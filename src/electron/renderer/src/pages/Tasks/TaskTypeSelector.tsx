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
  PictureOutlined,
} from "@ant-design/icons";

const { Text } = Typography;

export interface TaskTypeOption {
  key: string;
  title: string;
  description: string;
  icon: React.ReactNode;
}

export const TASK_TYPES: TaskTypeOption[] = [
  {
    key: "subtitle",
    title: "Subtitle Generator",
    description: "Generate subtitles from video files",
    icon: <SoundOutlined style={{ fontSize: 32 }} />,
  },
  {
    key: "audio",
    title: "Audio Extractor",
    description: "Extract audio from video files",
    icon: <AudioOutlined style={{ fontSize: 32 }} />,
  },
  {
    key: "transcribe",
    title: "Speech to Text",
    description: "Convert speech to text (SRT format)",
    icon: <SoundOutlined style={{ fontSize: 32 }} />,
  },
  {
    key: "translate",
    title: "Subtitle Translator",
    description: "Translate SRT subtitle files",
    icon: <TranslationOutlined style={{ fontSize: 32 }} />,
  },
  {
    key: "enhance",
    title: "Video Enhancement",
    description: "Enhance video quality with AI upscaling",
    icon: <VideoCameraOutlined style={{ fontSize: 32 }} />,
  },
];

interface TaskTypeSelectorProps {
  onSelect: (typeKey: string) => void;
}

const TaskTypeSelector: React.FC<TaskTypeSelectorProps> = ({ onSelect }) => {
  const { token } = theme.useToken();

  return (
    <Row gutter={[16, 16]} justify="center">
      {TASK_TYPES.map((type) => (
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
