"""
任务管理器

管理后台任务的生命周期、执行和进度跟踪。
支持创建不自动执行、手动启动单个/全部任务、串行队列执行。
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from mediafactory.api.schemas import TaskConfig, TaskProgress, TaskResult, TaskStatus, TaskType
from mediafactory.api.websocket import manager as ws_manager
from mediafactory.core.tool import CancellationToken
from mediafactory.api.error_handler import sanitize_error
from mediafactory.i18n import t

logger = logging.getLogger(__name__)

# stage 进度到全局进度的映射范围
STAGE_RANGES = {
    "model_loading": (0.0, 10.0),
    "audio_extraction": (10.0, 20.0),
    "transcription": (20.0, 70.0),
    "translation": (70.0, 95.0),
    "srt_generation": (95.0, 100.0),
    "video_enhancement": (0.0, 100.0),
    "download": (0.0, 100.0),
}


@dataclass
class Task:
    """任务内部表示"""

    id: str
    config: TaskConfig
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    name: str = ""  # 任务名称（创建时设定，不变）
    message: str = ""  # 实时状态消息（运行时更新）
    stage: Optional[str] = None
    result: Optional[TaskResult] = None
    cancel_token: CancellationToken = field(default_factory=CancellationToken)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    # 批处理相关
    file_index: int = 0
    total_files: int = 1


class TaskManager:
    """任务管理器"""

    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._running_task_id: Optional[str] = None
        self._queue: List[str] = []  # 待执行任务队列
        self._is_processing_queue: bool = False
        self._lock = asyncio.Lock()

    async def create_task(self, config: TaskConfig, name: Optional[str] = None) -> str:
        """创建新任务（不自动启动，保持 PENDING 状态）"""
        task_id = str(uuid.uuid4())[:8]
        task = Task(
            id=task_id,
            config=config,
            status=TaskStatus.PENDING,
            name=name or f"Task {task_id}",
        )
        async with self._lock:
            self._tasks[task_id] = task
        logger.info(f"Created task {task_id}: {config.task_type}")
        return task_id

    async def start_single_task(self, task_id: str) -> bool:
        """启动单个 PENDING 任务"""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return False

            if task.status != TaskStatus.PENDING:
                logger.warning(
                    f"Task {task_id} is not PENDING (status: {task.status})"
                )
                return False

            if self._running_task_id:
                logger.warning(f"Another task is running: {self._running_task_id}")
                return False

            self._running_task_id = task_id

        # 获取执行器
        from mediafactory.api.task_executor import get_executor

        executor = get_executor(task.config.task_type)
        if not executor:
            logger.error(f"No executor for task type: {task.config.task_type}")
            async with self._lock:
                if self._running_task_id == task_id:
                    self._running_task_id = None
            return False

        # 异步执行
        asyncio.create_task(self._execute_task(task_id, executor))
        return True

    async def start_all_pending(self) -> int:
        """启动所有 PENDING 任务（串行执行）"""
        async with self._lock:
            pending_ids = [
                tid
                for tid, t in self._tasks.items()
                if t.status == TaskStatus.PENDING
            ]
            # 添加到队列（去重）
            for tid in pending_ids:
                if tid not in self._queue:
                    self._queue.append(tid)

        logger.info(f"Queued {len(pending_ids)} tasks for execution")
        # 开始处理队列
        await self._process_next_in_queue()
        return len(pending_ids)

    async def _process_next_in_queue(self):
        """处理队列中的下一个任务（串行链式调用）"""
        task_id_to_run = None

        async with self._lock:
            if self._running_task_id:
                # 有任务在运行，等它完成后在 finally 中触发
                return

            if not self._queue:
                self._is_processing_queue = False
                return

            self._is_processing_queue = True

            # 取出第一个仍是 PENDING 的任务
            while self._queue:
                tid = self._queue.pop(0)
                task = self._tasks.get(tid)
                if task and task.status == TaskStatus.PENDING:
                    self._running_task_id = tid
                    task_id_to_run = tid
                    break
            else:
                # 队列中没有有效的 PENDING 任务
                self._is_processing_queue = False

        # 在锁外执行任务
        if task_id_to_run:
            task = self._tasks.get(task_id_to_run)
            if task:
                from mediafactory.api.task_executor import get_executor

                executor = get_executor(task.config.task_type)
                if executor:
                    asyncio.create_task(self._execute_task(task_id_to_run, executor))
                else:
                    logger.error(
                        f"No executor for task type: {task.config.task_type}"
                    )
                    async with self._lock:
                        self._running_task_id = None
                        self._is_processing_queue = False

    async def _execute_task(
        self,
        task_id: str,
        executor: Callable[[TaskConfig, "ProgressCallback"], Any],
    ):
        """内部方法：执行单个任务，完成后自动触发队列下一个"""
        task = self._tasks.get(task_id)
        if not task:
            return

        task.status = TaskStatus.RUNNING
        task.started_at = time.time()

        # 创建进度回调（async，在线程中通过 run_coroutine_threadsafe 调度）
        main_loop = asyncio.get_running_loop()

        async def _async_progress(progress: float, message: str = "", stage: str = ""):
            # 将 stage 级进度映射到全局进度
            if stage and stage in STAGE_RANGES:
                start, end = STAGE_RANGES[stage]
                progress = start + (progress / 100.0) * (end - start)
            task.progress = progress
            task.message = message
            task.stage = stage
            await ws_manager.broadcast_progress(
                task_id=task_id,
                status=task.status.value,
                progress=progress,
                message=message,
                stage=stage,
                file_index=task.file_index,
                total_files=task.total_files,
            )

        def progress_callback(progress: float, message: str = "", stage: str = ""):
            # 同步包装，将 async 回调调度到主事件循环
            # 使用默认参数捕获当前值，避免闭包变量在 lambda 执行时改变
            main_loop.call_soon_threadsafe(
                lambda p=progress, m=message, s=stage: asyncio.ensure_future(
                    _async_progress(p, m, s)
                )
            )

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                executor,
                task.config,
                progress_callback,
                task.cancel_token,
            )

            # 仅在未被取消时才处理结果（避免覆盖 CANCELLED 状态）
            if task.status != TaskStatus.CANCELLED:
                executor_success = result.get("success", False) if result else False
                if executor_success:
                    task.result = TaskResult(
                        task_id=task_id,
                        success=True,
                        output_path=result.get("output_path") if result else None,
                        metadata=result or {},
                    )
                    task.status = TaskStatus.COMPLETED
                    task.progress = 100
                else:
                    task.result = TaskResult(
                        task_id=task_id,
                        success=False,
                        error=result.get("error", "Unknown error") if result else t("error.noResultReturned"),
                        error_type="ProcessingError",
                    )
                    task.status = TaskStatus.FAILED

        except asyncio.CancelledError:
            if task.status != TaskStatus.CANCELLED:
                task.status = TaskStatus.CANCELLED
            task.result = TaskResult(
                task_id=task_id,
                success=False,
                error=t("task.cancelled"),
                error_type="CancelledError",
            )

        except Exception as e:
            logger.exception(f"Task {task_id} failed: {e}")
            if task.status != TaskStatus.CANCELLED:
                task.status = TaskStatus.FAILED
                task.result = TaskResult(
                    task_id=task_id,
                    success=False,
                    error=sanitize_error(e),
                    error_type=type(e).__name__,
                )

        finally:
            task.completed_at = time.time()
            async with self._lock:
                if self._running_task_id == task_id:
                    self._running_task_id = None

            # 广播完成
            await ws_manager.broadcast_task_complete(
                task_id=task_id,
                success=task.status == TaskStatus.COMPLETED,
                output_path=task.result.output_path if task.result else None,
                error=task.result.error if task.result else None,
            )

            # 自动触发队列中的下一个任务
            await self._process_next_in_queue()

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self._tasks.get(task_id)
        if not task:
            return False

        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            return False

        # 从队列中移除
        async with self._lock:
            if task_id in self._queue:
                self._queue.remove(task_id)

        task.cancel_token.cancel()
        task.status = TaskStatus.CANCELLED
        logger.info(f"Task {task_id} cancellation requested")

        # 通知前端取消状态
        await ws_manager.broadcast_progress(
            task_id=task_id,
            status=TaskStatus.CANCELLED.value,
            progress=task.progress,
            message=t("task.cancelled"),
            stage="",
            file_index=task.file_index,
            total_files=task.total_files,
        )
        await ws_manager.broadcast_task_complete(
            task_id=task_id,
            success=False,
            error=t("task.cancelled"),
        )
        return True

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress: Optional[float] = None,
        stage: Optional[str] = None,
        result: Optional[TaskResult] = None,
    ) -> bool:
        """更新任务状态（供 API 路由使用，替代直接访问 _tasks）。

        Args:
            task_id: 任务 ID
            status: 新状态
            progress: 可选进度值
            stage: 可选阶段名称
            result: 可选任务结果

        Returns:
            True 如果任务存在且已更新
        """
        task = self._tasks.get(task_id)
        if not task:
            return False

        task.status = status
        if progress is not None:
            task.progress = progress
        if stage is not None:
            task.stage = stage
        if result is not None:
            task.result = result
        if status == TaskStatus.RUNNING and task.started_at is None:
            task.started_at = time.time()
        if status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            task.completed_at = time.time()
        return True

    async def update_task_config(
        self, task_id: str, update_data: Dict[str, Any]
    ) -> bool:
        """更新 PENDING 任务的配置（仅允许修改可变参数）"""
        task = self._tasks.get(task_id)
        if not task:
            return False

        if task.status != TaskStatus.PENDING:
            logger.warning(
                f"Cannot edit task {task_id}: status is {task.status.value}"
            )
            return False

        # 更新可变字段
        for key, value in update_data.items():
            if hasattr(task.config, key):
                setattr(task.config, key, value)

        logger.info(f"Updated task {task_id} config: {list(update_data.keys())}")
        return True

    async def get_task_config(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务配置（用于编辑回显）"""
        task = self._tasks.get(task_id)
        if not task:
            return None
        return task.config.model_dump()

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态（包含前端需要的完整字段）"""
        task = self._tasks.get(task_id)
        if not task:
            return None

        result = {
            "id": task.id,
            "name": task.name,
            "type": task.config.task_type.value,
            "inputPath": task.config.input_path,
            "outputPath": task.result.output_path if task.result else None,
            "status": task.status.value,
            "progress": task.progress,
            "message": task.message,
            "error": task.result.error if task.result else None,
            "stage": task.stage,
        }
        return result

    async def get_all_tasks(
        self, exclude_types: Optional[list[TaskType]] = None
    ) -> list[Dict[str, Any]]:
        """获取所有任务状态（包含前端需要的完整字段）

        Args:
            exclude_types: 要排除的任务类型列表
        """
        tasks = self._tasks.values()
        if exclude_types:
            tasks = [t for t in tasks if t.config.task_type not in exclude_types]
        return [
            {
                "id": task.id,
                "name": task.name,
                "type": task.config.task_type.value,
                "inputPath": task.config.input_path,
                "outputPath": task.result.output_path if task.result else None,
                "status": task.status.value,
                "progress": task.progress,
                "message": task.message,
                "error": task.result.error if task.result else None,
                "stage": task.stage,
            }
            for task in tasks
        ]

    async def remove_task(self, task_id: str) -> bool:
        """移除任务"""
        async with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                if task.status == TaskStatus.RUNNING:
                    return False
                # 同时从队列中移除
                if task_id in self._queue:
                    self._queue.remove(task_id)
                del self._tasks[task_id]
                return True
        return False

    async def shutdown(self):
        """关闭时取消所有运行中的任务"""
        async with self._lock:
            self._queue.clear()
            for task in self._tasks.values():
                if task.status == TaskStatus.RUNNING:
                    task.cancel_token.cancel()
                    task.status = TaskStatus.CANCELLED
