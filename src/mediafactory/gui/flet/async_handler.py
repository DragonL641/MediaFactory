"""
异步任务处理器

在 Flet 中管理后台任务，支持进度更新和取消。
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union
from enum import Enum
from datetime import datetime
import uuid

import flet as ft

from mediafactory.logging import log_info, log_error


class TaskState(Enum):
    """任务状态"""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AsyncTask:
    """异步任务"""

    id: str
    name: str
    coroutine: Callable
    state: TaskState = TaskState.PENDING
    progress: float = 0.0
    message: str = ""
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 回调
    on_progress: Optional[Callable[[float, str], None]] = None
    on_complete: Optional[Callable[[Any], None]] = None
    on_error: Optional[Callable[[str], None]] = None


# 进度回调类型 - 接受 (progress, message) 参数
ProgressCallback = Callable[[float, str], Awaitable[None]]


class AsyncTaskManager:
    """
    异步任务管理器

    管理所有后台任务，支持进度更新和取消。

    使用方式：
        # 方式1：execute() 一步创建并执行
        await manager.execute(
            task_id="task-1",
            name="My Task",
            coroutine=lambda cb: my_async_func(cb),
            on_progress=lambda p, m: print(f"{p}%: {m}"),
            on_complete=lambda r: print(f"Done: {r}"),
            on_error=lambda e: print(f"Error: {e}"),
        )

        # 方式2：分步创建和执行
        task = manager.create_task(name="My Task", coroutine=...)
        await manager.run_task(task.id)
    """

    def __init__(self, page: ft.Page):
        self.page = page
        self._tasks: Dict[str, AsyncTask] = {}
        self._running_task: Optional[AsyncTask] = None
        self._cancel_requested: bool = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._task_lock: asyncio.Lock = asyncio.Lock()  # 任务执行锁

    @property
    def tasks(self) -> List[AsyncTask]:
        """获取所有任务"""
        return list(self._tasks.values())

    @property
    def running_task(self) -> Optional[AsyncTask]:
        """获取当前运行的任务"""
        return self._running_task

    @property
    def is_running(self) -> bool:
        """是否有任务在运行"""
        return self._running_task is not None

    def create_task(
        self,
        name: str,
        coroutine: Callable,
        on_progress: Optional[Callable[[float, str], None]] = None,
        on_complete: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> AsyncTask:
        """创建新任务"""
        task_id = str(uuid.uuid4())[:8]
        task = AsyncTask(
            id=task_id,
            name=name,
            coroutine=coroutine,
            on_progress=on_progress,
            on_complete=on_complete,
            on_error=on_error,
        )
        self._tasks[task_id] = task
        return task

    async def execute(
        self,
        task_id: str,
        name: str,
        coroutine: Callable[[ProgressCallback], Awaitable[Any]],
        on_progress: Optional[Callable[[float, str], None]] = None,
        on_complete: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        一步创建并执行任务（推荐使用）

        Args:
            task_id: 任务ID
            name: 任务名称
            coroutine: 异步协程函数，接受 progress_callback 参数
            on_progress: 进度回调 (progress: float, message: str)
            on_complete: 完成回调 (result: Any)
            on_error: 错误回调 (error: str)
        """
        # 创建任务
        task = AsyncTask(
            id=task_id,
            name=name,
            coroutine=coroutine,
            on_progress=on_progress,
            on_complete=on_complete,
            on_error=on_error,
        )
        self._tasks[task_id] = task

        # 执行任务
        await self._run_task_internal(task)

    async def run_task(self, task_id: str) -> None:
        """运行已创建的任务"""
        task = self._tasks.get(task_id)
        if not task:
            log_error(f"任务不存在: {task_id}")
            return
        await self._run_task_internal(task)

    async def _run_task_internal(self, task: AsyncTask) -> None:
        """内部方法：执行任务（使用锁实现串行执行）"""
        # 使用锁确保任务串行执行，后续任务会等待前一个任务完成
        async with self._task_lock:
            task.state = TaskState.RUNNING
            task.started_at = datetime.now()
            self._running_task = task
            self._cancel_requested = False

            try:
                # 创建进度回调
                async def progress_callback(progress: float, message: str = ""):
                    if self._cancel_requested:
                        raise asyncio.CancelledError("用户取消")
                    task.progress = progress
                    task.message = message
                    if task.on_progress:
                        task.on_progress(progress, message)
                    self._update_ui()

                # 执行任务
                result = await task.coroutine(progress_callback)
                task.result = result
                task.state = TaskState.COMPLETED
                task.completed_at = datetime.now()
                task.progress = 100.0

                if task.on_complete:
                    task.on_complete(result)

                log_info(f"任务完成: {task.name}")

            except asyncio.CancelledError:
                task.state = TaskState.CANCELLED
                task.message = "已取消"
                log_info(f"任务取消: {task.name}")

            except Exception as e:
                task.state = TaskState.FAILED
                task.error = str(e)
                task.message = f"错误: {e}"
                log_error(f"任务失败: {task.name} - {e}")
                if task.on_error:
                    task.on_error(str(e))

            finally:
                self._running_task = None
                self._update_ui()

    def cancel_task(self, task_id: str) -> None:
        """取消任务"""
        task = self._tasks.get(task_id)
        if not task:
            return

        if task == self._running_task:
            self._cancel_requested = True
            log_info(f"请求取消任务: {task.name}")

    def remove_task(self, task_id: str) -> None:
        """移除任务"""
        if task_id in self._tasks:
            task = self._tasks[task_id]
            if task.state == TaskState.RUNNING:
                self.cancel_task(task_id)
            del self._tasks[task_id]

    def clear_completed(self) -> None:
        """清除已完成的任务"""
        completed_ids = [
            tid
            for tid, task in self._tasks.items()
            if task.state
            in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED]
        ]
        for tid in completed_ids:
            del self._tasks[tid]

    def _update_ui(self) -> None:
        """更新 UI"""
        try:
            self.page.update()
        except Exception:
            pass


def create_progress_callback(
    task: AsyncTask,
    page: ft.Page,
) -> Callable[[float, str], None]:
    """创建进度回调函数"""

    def callback(progress: float, message: str = ""):
        task.progress = progress
        task.message = message
        if task.on_progress:
            task.on_progress(progress, message)
        try:
            page.update()
        except Exception:
            pass

    return callback
