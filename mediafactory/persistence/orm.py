"""任务历史 ORM 模型

SQLAlchemy 2.0 typed style（Mapped[]/mapped_column）。
独立于 api/task_store.py 的持久队列表：历史库只追加终态记录，
用户在任务页「清除」不会影响历史。
"""

from __future__ import annotations

from sqlalchemy import Float, Index, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """历史库声明基类"""


class TaskHistoryORM(Base):
    """任务历史表（task_history）"""

    __tablename__ = "task_history"

    # 代理主键：列表排序/删除用；业务键是 task_id
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # 任务 ID（retry 重跑同 id → upsert 覆盖为最新一次结果）
    task_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    # TaskType.value：subtitle/audio/transcribe/translate/enhance/download
    task_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # 终态：completed/failed/cancelled
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    input_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    output_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    error: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # TaskResult.metadata 的 JSON 快照
    metadata_json: Mapped[str] = mapped_column(
        String(4096), nullable=False, default="{}"
    )
    # epoch 秒（沿袭 tasks 表惯例）
    created_at: Mapped[float] = mapped_column(Float, nullable=False)
    started_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    completed_at: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (Index("idx_task_history_completed_at", "completed_at"),)
