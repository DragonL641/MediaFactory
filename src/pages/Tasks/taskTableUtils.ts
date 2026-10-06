/**
 * 任务表格工具：相对时间、过滤链、日志行级别解析、类型配色
 */

import type { Task } from "../../types";

export function formatRelativeTime(epochSeconds?: number): string {
  if (!epochSeconds) return "—";
  const diff = Date.now() / 1000 - epochSeconds;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 7 * 86400) return `${Math.floor(diff / 86400)}d ago`;
  return new Date(epochSeconds * 1000).toISOString().slice(0, 10);
}

export function filterTasks(
  tasks: Task[],
  typeFilter: string,
  statusFilter: string,
  query: string
): Task[] {
  const q = query.trim().toLowerCase();
  return tasks.filter(
    (t) =>
      (typeFilter === "all" || t.type === typeFilter) &&
      (statusFilter === "all" || t.status === statusFilter) &&
      (!q || (t.name || "").toLowerCase().includes(q))
  );
}

/** 提取日志行级别（`| LEVEL |` 标记）；非标准行返回 null（恒显处理） */
export function parseLogLevel(line: string): string | null {
  const m = line.match(/\|\s+(INFO|WARNING|ERROR|DEBUG|SUCCESS)\s+\|/);
  return m ? m[1] : null;
}

export const TYPE_TAG_COLORS: Record<string, string> = {
  audio: "geekblue",
  transcribe: "cyan",
  translate: "purple",
  subtitle: "green",
  enhance: "orange",
};
