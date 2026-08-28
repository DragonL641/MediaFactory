"""模型下载后台任务。

业务逻辑从 routes/models.py 下沉至此：任务创建后立即在后台执行
（不进任务队列，可与处理任务并行），进度经节流后通过 WebSocket 广播。

注意：下载任务不支持取消/重试（cancel_task 置 CANCELLED 后下载仍会完成并
覆写状态；retry_task 因 runner 无 DOWNLOAD 注册而卡在 PENDING）。
"""

import asyncio
import functools
import logging
import time
from typing import Callable, Optional

from mediafactory.api.schemas import TaskConfig, TaskResult, TaskStatus, TaskType
from mediafactory.api.task_manager import get_task_manager
from mediafactory.api.websocket import manager as ws_manager
from mediafactory.core.error_utils import sanitize_error
from mediafactory.i18n import t

logger = logging.getLogger(__name__)

# 并发下载保护：正在下载的模型集合
_active_downloads: set[str] = set()

_PROGRESS_THROTTLE_SEC = 0.5


def active_downloads() -> set[str]:
    """当前正在下载的模型 ID 集合（副本）"""
    return set(_active_downloads)


async def start_download(
    model_id: str,
    endpoint: Optional[str],
    on_complete: Optional[Callable[[], None]] = None,
) -> str:
    """创建并立即启动模型下载任务。

    Args:
        model_id: 模型 ID
        endpoint: 镜像源地址（None 表示官方源）
        on_complete: 下载成功后的回调（如缓存失效）
    Returns:
        任务 ID
    """
    task_manager = get_task_manager()
    config = TaskConfig(task_type=TaskType.DOWNLOAD, input_path=model_id)
    task_id = await task_manager.create_task(
        config, name=t("task.downloadingModel", modelId=model_id)
    )

    _active_downloads.add(model_id)
    asyncio.create_task(
        _execute_download_task(task_id, model_id, endpoint, on_complete)
    )
    return task_id


async def _execute_download_task(
    task_id: str,
    model_id: str,
    endpoint: Optional[str],
    on_complete: Optional[Callable[[], None]],
):
    """执行模型下载任务。"""
    # 重量级 HF 依赖，保留局部导入以延迟加载
    from mediafactory.models.model_download import download_model

    task_manager = get_task_manager()
    loop = asyncio.get_running_loop()

    await task_manager.update_task_status(task_id, TaskStatus.RUNNING)

    async def _progress_callback(progress: float, msg: str = ""):
        await ws_manager.broadcast_progress(
            task_id=task_id,
            status="downloading",
            progress=progress * 100,
            message=msg,
            stage="download",
        )

    try:
        _last_progress_time = [0.0]

        def sync_progress(p: float, m: str = ""):
            # 从下载线程安全地调度到主事件循环，带 500ms 节流
            now = time.monotonic()
            if p < 0.99 and (now - _last_progress_time[0]) < _PROGRESS_THROTTLE_SEC:
                return
            _last_progress_time[0] = now
            loop.call_soon_threadsafe(
                lambda: asyncio.ensure_future(_progress_callback(p, m))
            )

        await loop.run_in_executor(
            None,
            functools.partial(
                download_model,
                model_id,
                download_source=endpoint,
                progress_callback=sync_progress,
            ),
        )

        if on_complete:
            on_complete()

        await task_manager.update_task_status(
            task_id,
            TaskStatus.COMPLETED,
            progress=100,
            stage="download",
            result=TaskResult(
                task_id=task_id,
                success=True,
                output_path=f"models/{model_id}",
            ),
        )
        await ws_manager.broadcast_task_complete(
            task_id=task_id,
            success=True,
            output_path=f"models/{model_id}",
        )

    except Exception as e:
        logger.exception(f"Download failed: {e}")
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
            task_id=task_id,
            success=False,
            error=sanitize_error(e),
        )
    finally:
        _active_downloads.discard(model_id)
