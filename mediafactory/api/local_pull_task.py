"""Ollama 模型拉取后台任务。

镜像 download_task.py 的"任务 + WS 进度"模式，差异：
- 进度源是 Ollama /api/pull 的 NDJSON 流（completed/total 字段）
- 支持取消：协程轮询任务状态，发现 CANCELLED 即停止消费流——
  断开 HTTP 流后 Ollama 自动中止 pull，已下载分片由其断点续传保留
"""

import asyncio
import logging
import time
from collections.abc import Callable

from mediafactory.api.schemas import TaskConfig, TaskResult, TaskStatus, TaskType
from mediafactory.api.task_manager import get_task_manager
from mediafactory.api.websocket import manager as ws_manager
from mediafactory.core.error_utils import sanitize_error
from mediafactory.llm.ollama_client import get_ollama_client

logger = logging.getLogger(__name__)

# 并发保护：正在拉取的模型名集合
_active_pulls: set[str] = set()

_PROGRESS_THROTTLE_SEC = 0.5


def active_pulls() -> set[str]:
    """当前正在拉取的模型名集合（副本）"""
    return set(_active_pulls)


async def start_pull(name: str, on_complete: Callable[[], None] | None = None) -> str:
    """创建并立即启动 Ollama 拉取任务。返回任务 ID。"""
    task_manager = get_task_manager()
    config = TaskConfig(task_type=TaskType.DOWNLOAD, input_path=name)
    task_id = await task_manager.create_task(config, name=f"Pull model: {name}")

    _active_pulls.add(name)
    asyncio.create_task(_execute_pull_task(task_id, name, on_complete))
    return task_id


async def _execute_pull_task(
    task_id: str, name: str, on_complete: Callable[[], None] | None
) -> None:
    """消费 pull 流并广播进度。"""
    task_manager = get_task_manager()
    client = get_ollama_client()

    await task_manager.update_task_status(task_id, TaskStatus.RUNNING)
    logger.info(f"Pulling Ollama model: {name}")

    last_progress_time = 0.0
    try:
        async for event in client.pull_stream(name):
            # 取消检查：cancel_task 已把状态置 CANCELLED，此时直接退出，
            # 不再写状态（避免覆盖取消终态）
            status_info = await task_manager.get_task_status(task_id)
            if status_info and status_info.get("status") == TaskStatus.CANCELLED.value:
                logger.info(f"Pull of {name} cancelled, closing stream")
                return

            completed, total = event.get("completed"), event.get("total")
            now = time.monotonic()
            if (
                isinstance(completed, int)
                and isinstance(total, int)
                and total > 0
                and now - last_progress_time >= _PROGRESS_THROTTLE_SEC
            ):
                last_progress_time = now
                await ws_manager.broadcast_progress(
                    task_id=task_id,
                    status="downloading",
                    progress=completed / total * 100.0,
                    message=event.get("status", ""),
                    stage="download",
                )

        await task_manager.update_task_status(
            task_id,
            TaskStatus.COMPLETED,
            progress=100,
            stage="download",
            result=TaskResult(
                task_id=task_id,
                success=True,
                output_path=f"ollama:{name}",
            ),
        )
        await ws_manager.broadcast_task_complete(
            task_id=task_id, success=True, output_path=f"ollama:{name}"
        )
        if on_complete:
            on_complete()

    except Exception as e:
        logger.exception(f"Pull of {name} failed: {e}")
        await task_manager.update_task_status(
            task_id,
            TaskStatus.FAILED,
            stage="download",
            result=TaskResult(
                task_id=task_id,
                success=False,
                error=sanitize_error(e),
                error_type=type(e).__name__,
            ),
        )
        await ws_manager.broadcast_task_complete(
            task_id=task_id, success=False, error=sanitize_error(e)
        )
    finally:
        _active_pulls.discard(name)
