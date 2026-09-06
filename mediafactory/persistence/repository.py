"""任务历史仓储

async SQLAlchemy 2.0（aiosqlite）实现。所有方法自包含会话，
调用方无需管理事务。db_path 为 None 时用内存库（测试隔离，
对齐 api/task_store.py 惯例）。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool

from mediafactory.persistence.orm import Base, TaskHistoryORM

if TYPE_CHECKING:
    from mediafactory.api.task_manager import Task

logger = logging.getLogger(__name__)

# 终态集合：只有这些状态会写入历史
TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


@dataclass
class TaskHistoryEntry:
    """历史记录（ORM 无关的纯数据类，路由/测试不碰 ORM）"""

    task_id: str
    name: str
    task_type: str
    status: str
    input_path: str | None
    output_path: str | None
    error: str | None
    error_type: str | None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    started_at: float | None = None
    completed_at: float = 0.0
    # ORM 代理主键（读取时回填；构造写入时无需）
    id: int | None = None


def history_entry_from_task(task: Task) -> TaskHistoryEntry:
    """从 TaskManager 的 Task 构造历史条目。

    依赖方向保持 api → persistence 单向：Task 仅在类型标注中引用
    （TYPE_CHECKING），运行时鸭子类型访问所需属性。
    """
    result = task.result
    return TaskHistoryEntry(
        task_id=task.id,
        name=task.name,
        task_type=task.config.task_type.value,
        status=task.status.value,
        input_path=task.config.input_path,
        output_path=result.output_path if result else None,
        error=result.error if result else None,
        error_type=result.error_type if result else None,
        metadata=dict(result.metadata) if result else {},
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at if task.completed_at is not None else 0.0,
    )


class HistoryRepository:
    """任务历史仓储（独立 history.db，写终态、查列表、删单条/清空）"""

    def __init__(self, db_path: Path | None = None) -> None:
        """db_path 为 None 时用内存库（测试隔离）。"""
        self._db_path = db_path
        self._engine: AsyncEngine | None = None
        self._schema_ready = False

    def _get_engine(self) -> AsyncEngine:
        if self._engine is None:
            if self._db_path is None:
                # 内存库：StaticPool 复用单连接，否则每个连接各见一个空库
                self._engine = create_async_engine(
                    "sqlite+aiosqlite://",
                    poolclass=StaticPool,
                    connect_args={"check_same_thread": False},
                )
            else:
                self._db_path.parent.mkdir(parents=True, exist_ok=True)
                self._engine = create_async_engine(
                    f"sqlite+aiosqlite:///{self._db_path}"
                )
        return self._engine

    async def _ensure_schema(self) -> None:
        """首次调用时建表（create_all 幂等）。"""
        if self._schema_ready:
            return
        engine = self._get_engine()

        def _create(sync_conn):  # noqa: ANN001
            Base.metadata.create_all(sync_conn)

        async with engine.begin() as conn:
            await conn.run_sync(_create)
        self._schema_ready = True

    async def upsert(self, entry: TaskHistoryEntry) -> None:
        """写入/覆盖一条终态记录（task_id 唯一，retry 重跑覆盖旧结果）。"""
        await self._ensure_schema()
        values = {
            "task_id": entry.task_id,
            "name": entry.name,
            "task_type": entry.task_type,
            "status": entry.status,
            "input_path": entry.input_path,
            "output_path": entry.output_path,
            "error": entry.error,
            "error_type": entry.error_type,
            "metadata_json": json.dumps(entry.metadata or {}, ensure_ascii=False),
            "created_at": entry.created_at,
            "started_at": entry.started_at,
            "completed_at": entry.completed_at,
        }
        stmt = sqlite_insert(TaskHistoryORM).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[TaskHistoryORM.task_id], set_=values
        )
        async with self._get_engine().begin() as conn:
            await conn.execute(stmt)

    async def list_records(
        self,
        limit: int = 50,
        offset: int = 0,
        *,
        status: str | None = None,
        task_type: str | None = None,
    ) -> tuple[list[TaskHistoryEntry], int]:
        """分页列出历史（completed_at 降序），返回 (条目, 总数)。"""
        await self._ensure_schema()
        conditions = []
        if status:
            conditions.append(TaskHistoryORM.status == status)
        if task_type:
            conditions.append(TaskHistoryORM.task_type == task_type)

        async with self._get_engine().connect() as conn:
            total = (
                await conn.execute(
                    select(func.count()).select_from(TaskHistoryORM).where(*conditions)
                )
            ).scalar_one()
            rows = (
                (
                    await conn.execute(
                        select(TaskHistoryORM)
                        .where(*conditions)
                        .order_by(
                            TaskHistoryORM.completed_at.desc(), TaskHistoryORM.id.desc()
                        )
                        .limit(limit)
                        .offset(offset)
                    )
                )
                .mappings()
                .all()
            )
        return [_row_to_entry(row) for row in rows], total

    async def get_record(self, task_id: str) -> TaskHistoryEntry | None:
        await self._ensure_schema()
        async with self._get_engine().connect() as conn:
            row = (
                (
                    await conn.execute(
                        select(TaskHistoryORM).where(TaskHistoryORM.task_id == task_id)
                    )
                )
                .mappings()
                .first()
            )
        return _row_to_entry(row) if row else None

    async def delete_record(self, task_id: str) -> bool:
        await self._ensure_schema()
        async with self._get_engine().begin() as conn:
            result = await conn.execute(
                delete(TaskHistoryORM).where(TaskHistoryORM.task_id == task_id)
            )
        return result.rowcount > 0

    async def clear(self) -> int:
        """清空历史，返回删除条数。"""
        await self._ensure_schema()
        async with self._get_engine().begin() as conn:
            total = (
                await conn.execute(select(func.count()).select_from(TaskHistoryORM))
            ).scalar_one()
            await conn.execute(delete(TaskHistoryORM))
        return total

    async def close(self) -> None:
        """释放引擎连接（lifespan 关闭段调用）。"""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._schema_ready = False


def _row_to_entry(row: Any) -> TaskHistoryEntry:
    """ORM 行 → 纯数据类。"""
    return TaskHistoryEntry(
        id=row["id"],
        task_id=row["task_id"],
        name=row["name"],
        task_type=row["task_type"],
        status=row["status"],
        input_path=row["input_path"],
        output_path=row["output_path"],
        error=row["error"],
        error_type=row["error_type"],
        metadata=json.loads(row["metadata_json"] or "{}"),
        created_at=row["created_at"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
    )


def epoch_to_iso(ts: float | None) -> str | None:
    """epoch 秒 → ISO 8601 UTC 字符串（API 输出用）。"""
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=UTC).isoformat()
