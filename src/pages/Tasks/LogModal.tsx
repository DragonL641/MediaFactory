/**
 * 任务日志弹框：等宽滚动区 + 1s 轮询 + 新内容自动滚底（手动上滚暂停，回底恢复）
 */

import React, { useEffect, useRef, useState } from "react";
import { Modal, Typography } from "antd";
import { useTranslation } from "react-i18next";
import { useTaskLogsQuery } from "../../api/queries";
import type { Task } from "../../types";

interface LogModalProps {
  open: boolean;
  onClose: () => void;
  task: Task;
}

const LogModal: React.FC<LogModalProps> = ({ open, onClose, task }) => {
  const { t } = useTranslation("tasks");
  const terminal = ["completed", "failed", "cancelled"].includes(task.status);
  const { data } = useTaskLogsQuery(task.id, open && !terminal);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [stickBottom, setStickBottom] = useState(true);

  const lines = data?.lines ?? [];

  useEffect(() => {
    if (stickBottom && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [lines.length, stickBottom]);

  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 24;
    setStickBottom(atBottom);
  };

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width={720}
      title={`${t("card.viewLog")} — ${task.name}`}
    >
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        style={{
          maxHeight: "60vh",
          overflowY: "auto",
          background: "var(--mf-bg-container, #fafafa)",
          border: "1px solid var(--mf-border, #eee)",
          borderRadius: 6,
          padding: 12,
          fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
          fontSize: 12,
          lineHeight: 1.6,
          whiteSpace: "pre-wrap",
          wordBreak: "break-all",
        }}
      >
        {lines.length === 0 ? (
          <Typography.Text type="secondary">{t("card.noLogs")}</Typography.Text>
        ) : (
          lines.map((l, i) => <div key={i}>{l}</div>)
        )}
      </div>
      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
        {terminal ? t("card.logFinal") : t("card.logStreaming")}
      </Typography.Text>
    </Modal>
  );
};

export default LogModal;
