"""任务历史持久层

SQLAlchemy 2.0 async + aiosqlite。独立于 api/task_store.py 的持久队列：
历史库只追加终态记录，用户在任务页「清除」不影响历史。
"""

from mediafactory.persistence.db import (
    default_history_db_path,
    get_history_repository,
    reset_history_repository,
)
from mediafactory.persistence.repository import (
    TERMINAL_STATUSES,
    HistoryRepository,
    TaskHistoryEntry,
    epoch_to_iso,
    history_entry_from_task,
)

__all__ = [
    "TERMINAL_STATUSES",
    "HistoryRepository",
    "TaskHistoryEntry",
    "default_history_db_path",
    "epoch_to_iso",
    "get_history_repository",
    "history_entry_from_task",
    "reset_history_repository",
]
