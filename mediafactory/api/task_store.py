"""SQLite 任务持久化存储。

TaskManager 的持久层：任务记录与待执行队列落盘，
daemon 重启后可恢复（RUNNING→FAILED，QUEUED 原样保留）。
"""

import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

# 任务表 schema（config_json = TaskConfig.model_dump_json()）
_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    config_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    progress REAL NOT NULL DEFAULT 0,
    message TEXT NOT NULL DEFAULT '',
    stage TEXT,
    output_path TEXT,
    error TEXT,
    error_type TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    queued_at REAL,
    created_at REAL NOT NULL,
    started_at REAL,
    completed_at REAL
);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_queued ON tasks(queued_at);
"""

# SELECT 显式列清单（不依赖 schema 列序）
_COLUMNS = (
    "id, name, config_json, status, progress, message, stage, "
    "output_path, error, error_type, metadata_json, queued_at, "
    "created_at, started_at, completed_at"
)


class TaskStore:
    """SQLite 任务存储（单连接 + 线程锁，方法全部同步）。

    db_path 为 None 时使用内存库（测试隔离，不落盘）。
    """

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            self._conn = sqlite3.connect(":memory:", check_same_thread=False)
        else:
            db_path = Path(db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    def insert(self, task_id: str, name: str, config_json: str, created_at: float) -> None:
        """插入新任务行（status 默认 pending，不在队列）。"""
        with self._lock:
            self._conn.execute(
                "INSERT INTO tasks (id, name, config_json, created_at) VALUES (?, ?, ?, ?)",
                (task_id, name, config_json, created_at),
            )
            self._conn.commit()

    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        """按 id 取单行，不存在返回 None。"""
        with self._lock:
            row = self._conn.execute(
                f"SELECT {_COLUMNS} FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
        return dict(row) if row else None

    def get_all(self) -> List[Dict[str, Any]]:
        """取全部任务行。"""
        with self._lock:
            rows = self._conn.execute(f"SELECT {_COLUMNS} FROM tasks").fetchall()
        return [dict(r) for r in rows]
