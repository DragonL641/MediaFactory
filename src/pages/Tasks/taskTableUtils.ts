/**
 * 任务表格工具：相对时间、过滤链、日志行级别解析、类型配色
 */

import type { Task } from "../../types";

/** 统一时间格式：2026-09-12 14:36（本地时区） */
export function formatDateTime(epochSeconds?: number): string {
  if (!epochSeconds) return "—";
  const d = new Date(epochSeconds * 1000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
    `${pad(d.getHours())}:${pad(d.getMinutes())}`;
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
