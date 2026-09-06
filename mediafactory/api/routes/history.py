"""
任务历史 API 路由

提供历史查询、单条删除、清空端点。历史由 TaskManager 在任务终态时
自动写入（见 task_manager._record_history），本路由只读/删。
"""

import logging

from fastapi import APIRouter, HTTPException, Query

from mediafactory.api.schemas import HistoryListResponse, TaskHistoryItem
from mediafactory.i18n import t
from mediafactory.persistence import (
    HistoryRepository,
    epoch_to_iso,
    get_history_repository,
)

logger = logging.getLogger(__name__)
# API 层使用标准 logging，通过 InterceptHandler 自动重定向到 loguru

router = APIRouter()


def _get_repo() -> HistoryRepository:
    """获取全局历史仓储（模块级函数，测试 monkeypatch 点）"""
    return get_history_repository()


def _item_from_entry(entry) -> TaskHistoryItem:  # noqa: ANN001
    """历史条目 → API 模型（时间戳 ISO 化，时长 API 侧算好）"""
    duration_ms = None
    if entry.started_at is not None:
        duration_ms = max(0, int((entry.completed_at - entry.started_at) * 1000))
    return TaskHistoryItem(
        id=entry.id or 0,
        task_id=entry.task_id,
        name=entry.name,
        type=entry.task_type,
        status=entry.status,
        input_path=entry.input_path,
        output_path=entry.output_path,
        error=entry.error,
        error_type=entry.error_type,
        metadata=entry.metadata,
        created_at=epoch_to_iso(entry.created_at),
        started_at=epoch_to_iso(entry.started_at),
        completed_at=epoch_to_iso(entry.completed_at),
        duration_ms=duration_ms,
    )


@router.get("", response_model=HistoryListResponse)
async def list_history(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
    type: str | None = Query(None),
) -> HistoryListResponse:
    """分页查询任务历史（completed_at 降序）"""
    entries, total = await _get_repo().list_records(
        limit=limit, offset=offset, status=status, task_type=type
    )
    return HistoryListResponse(
        total=total, items=[_item_from_entry(e) for e in entries]
    )


@router.get("/{task_id}", response_model=TaskHistoryItem)
async def get_history_record(task_id: str) -> TaskHistoryItem:
    """查询单条历史记录"""
    entry = await _get_repo().get_record(task_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=t("history.notFound"))
    return _item_from_entry(entry)


@router.delete("/{task_id}")
async def delete_history_record(task_id: str) -> dict:
    """删除单条历史记录"""
    deleted = await _get_repo().delete_record(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=t("history.notFound"))
    return {"deleted": True}


@router.delete("")
async def clear_history() -> dict:
    """清空全部历史，返回删除条数"""
    n = await _get_repo().clear()
    return {"deleted": n}
