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

# 在飞拉取任务的强引用（asyncio 事件循环对 task 只持弱引用，
# 不保存引用则任务可能在挂起等待流数据时被 GC 静默回收）
_running_pull_tasks: set[asyncio.Task] = set()

# 模型名 → 任务 ID（供 /api/models/local 输出在飞拉取进度快照）
_pull_task_ids: dict[str, str] = dict()

_PROGRESS_THROTTLE_SEC = 0.5

# 看门狗：Ollama 正常拉取时进度事件是秒级连发的，
# 超过该时长无任何事件视为流死亡（框架层竞态/网络劣化）
_PULL_NO_EVENT_TIMEOUT_SEC = 30.0


def active_pulls() -> set[str]:
    """当前正在拉取的模型名集合（副本）"""
    return set(_active_pulls)


async def active_pull_details() -> list[dict]:
    """在飞拉取任务的进度快照（供 /api/models/local 展示）。"""
    if not _pull_task_ids:
        return []
    task_manager = get_task_manager()
    details: list[dict] = []
    for name, task_id in list(_pull_task_ids.items()):
        info = await task_manager.get_task_status(task_id)
        if not info:
            continue
        details.append(
            {
                "name": name,
                "progress": float(info.get("progress") or 0.0),
                "taskId": task_id,
            }
        )
    return details


async def start_pull(name: str, on_complete: Callable[[], None] | None = None) -> str:
    """创建并立即启动 Ollama 拉取任务。返回任务 ID。"""
    task_manager = get_task_manager()
    config = TaskConfig(task_type=TaskType.DOWNLOAD, input_path=name)
    task_id = await task_manager.create_task(config, name=f"Pull model: {name}")

    _active_pulls.add(name)
    _pull_task_ids[name] = task_id
    task = asyncio.create_task(_execute_pull_task(task_id, name, on_complete))
    _running_pull_tasks.add(task)
    task.add_done_callback(_running_pull_tasks.discard)
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

    async def _is_cancelled() -> bool:
        status_info = await task_manager.get_task_status(task_id)
        return bool(
            status_info and status_info.get("status") == TaskStatus.CANCELLED.value
        )

    # 三处终态写入前都要复查：cancel_task 可能恰好在最后一个事件之后、
    # 终态写入之前落地（update_task_status 无终态保护）
    try:
        agen = client.pull_stream(name)
        try:
            while True:
                # 逐事件看门狗：流死亡（框架层竞态/网络劣化）时不再无限等待
                try:
                    event = await asyncio.wait_for(
                        agen.__anext__(), timeout=_PULL_NO_EVENT_TIMEOUT_SEC
                    )
                except StopAsyncIteration:
                    break

                # 取消检查：cancel_task 已把状态置 CANCELLED，此时直接退出，
                # 不再写状态（避免覆盖取消终态）
                if await _is_cancelled():
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
        finally:
            await agen.aclose()

        if await _is_cancelled():
            logger.info(f"Pull of {name} cancelled just before completion")
            return

        # 完成后校验：流正常结束但模型不在位（空流假成功，框架层竞态实测）
        # 不得标 COMPLETED——把假成功变成可见失败
        if not await client.is_model_installed(name):
            error = f"pull of {name} ended but model is not installed in Ollama"
            logger.warning(error)
            await task_manager.update_task_status(
                task_id,
                TaskStatus.FAILED,
                stage="download",
                result=TaskResult(
                    task_id=task_id,
                    success=False,
                    error=error,
                    error_type="PullVerificationFailed",
                ),
            )
            await ws_manager.broadcast_task_complete(
                task_id=task_id, success=False, error=error
            )
            return

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

    except TimeoutError:
        if await _is_cancelled():
            # 网络劣化常与用户点取消同时发生：异常不得把 CANCELLED 翻转为 FAILED
            logger.info(f"Pull of {name} errored after cancellation, keeping CANCELLED")
            return
        error = (
            f"pull of {name} stalled: no stream events "
            f"for {_PULL_NO_EVENT_TIMEOUT_SEC:.0f}s"
        )
        logger.warning(error)
        await task_manager.update_task_status(
            task_id,
            TaskStatus.FAILED,
            stage="download",
            result=TaskResult(
                task_id=task_id,
                success=False,
                error=error,
                error_type="PullStalled",
            ),
        )
        await ws_manager.broadcast_task_complete(
            task_id=task_id, success=False, error=error
        )

    except Exception as e:
        if await _is_cancelled():
            # 网络劣化常与用户点取消同时发生：异常不得把 CANCELLED 翻转为 FAILED
            logger.info(f"Pull of {name} errored after cancellation, keeping CANCELLED")
            return
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
        _pull_task_ids.pop(name, None)
