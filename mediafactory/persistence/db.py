"""历史库引擎与单例装配

生产库落 data/history.db（daemon 重启后历史保留）；
单例延迟初始化，reset_history_repository() 供测试隔离。
"""

from __future__ import annotations

from pathlib import Path

from mediafactory.persistence.repository import HistoryRepository

_history_repository: HistoryRepository | None = None


def get_history_repository() -> HistoryRepository:
    """获取全局历史仓储单例（延迟初始化，生产装配）。"""
    global _history_repository
    if _history_repository is None:
        from mediafactory.config import get_data_root_dir

        _history_repository = HistoryRepository(
            db_path=get_data_root_dir() / "data" / "history.db"
        )
    return _history_repository


def reset_history_repository() -> None:
    """重置单例（测试隔离用）。"""
    global _history_repository
    _history_repository = None


def default_history_db_path() -> Path:
    """生产历史库路径（data/history.db，.gitignore 已覆盖 /data/）。"""
    from mediafactory.config import get_data_root_dir

    return get_data_root_dir() / "data" / "history.db"
