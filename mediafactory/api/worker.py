"""worker 子进程与执行器接缝。

ML 重活在与 daemon 隔离的子进程中执行：
- 子进程崩溃（段错误等）只导致当前任务 FAILED，daemon 与队列存活
- 进度/结果经 multiprocessing.Queue 回传（纯 dict，无 live 引用）
- 取消经 multiprocessing.Event（协作式，任务在检查点停下）

TaskManager 经 TaskExecutor 接缝调用：
- InlineExecutor：进程内执行（默认；测试与 RUNNERS monkeypatch 路径）
- WorkerProcessExecutor：子进程执行（生产装配）
"""

import asyncio
import logging
import multiprocessing as mp
import threading
import time
from typing import Any, Callable, Dict, Optional, Protocol

from mediafactory.api.schemas import TaskConfig
from mediafactory.core.tool import CancellationToken
from mediafactory.pipeline.context import ProcessingResult

logger = logging.getLogger(__name__)
# API 层使用标准 logging，通过 InterceptHandler 自动重定向到 loguru

# ==================== 子进程侧 ====================


class _WorkerProgress:
    """子进程侧进度回调：转发进度到 daemon，检查跨进程取消标志。

    实现 core.progress_protocol.ProgressCallback 协议形状。
    res_q 只要求有 put 方法（跨进程为 mp.Queue，测试可用 list.append）。
    """

    def __init__(self, task_id: str, res_q: Any, cancel_event: Any) -> None:
        self._task_id = task_id
        self._res_q = res_q
        self._cancel_event = cancel_event
        self._stage: str = ""

    def set_stage(self, stage: str) -> None:
        self._stage = stage

    def update(self, progress: float, message: str = "") -> None:
        if not self.is_cancelled():
            self._res_q.put(
                {
                    "kind": "progress",
                    "task_id": self._task_id,
                    "progress": float(progress),
                    "message": message,
                    "stage": self._stage,
                }
            )

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def cancel(self) -> None:
        self._cancel_event.set()


def _run_task_in_worker(
    task_id: str,
    config_dict: Dict[str, Any],
    res_q: Any,
    cancel_event: Any,
) -> Dict[str, Any]:
    """在子进程中执行单个任务，返回可跨进程传输的结果投影。

    ProcessingResult.context 持有 live 引用不可传输，此处只投影
    TaskManager 消费的字段。
    """
    from mediafactory.core.error_utils import sanitize_error
    from mediafactory.services import runner as runner_module

    config = TaskConfig.model_validate(config_dict)
    fn = runner_module.RUNNERS.get(config.task_type)
    progress = _WorkerProgress(task_id, res_q, cancel_event)

    async def _run() -> ProcessingResult:
        if fn is None:
            return ProcessingResult(
                success=False,
                error_message=f"No executor for task type: {config.task_type}",
                error_type="ConfigurationError",
            )
        return await fn(config, progress)

    try:
        result = asyncio.run(_run())
        return {
            "success": result.success,
            "output_path": result.output_path,
            "error_message": result.error_message or "",
            "error_type": result.error_type,
            "metadata": result.metadata or {},
        }
    except Exception as e:  # 直调引擎路径异常在此兜底并转用户消息
        from mediafactory.logging import log_exception

        # sanitize_error 内部的 stdlib logging 不落 logs/，完整 traceback 在此补记
        log_exception(f"Worker task failed: {task_id}")

        return {
            "success": False,
            "output_path": None,
            "error_message": sanitize_error(e),
            "error_type": type(e).__name__,
            "metadata": {},
        }


# ==================== 执行器接缝 ====================


class TaskExecutor(Protocol):
    """任务执行器接缝：TaskManager 经此分发任务。"""

    async def execute(
        self,
        task_id: str,
        config: TaskConfig,
        progress_callback: Callable[[float, str, str], None],
        cancel_token: CancellationToken,
    ) -> ProcessingResult:
        """执行任务，返回结果。progress_callback 线程安全可直调。"""
        ...

    def cancel(self, task_id: str) -> None:
        """请求取消当前运行的任务（无则忽略）。"""
        ...

    def shutdown(self) -> None:
        """释放执行器资源。"""
        ...


class InlineExecutor:
    """进程内执行（默认）：运行时查 RUNNERS 注册表，保持 monkeypatch 可用。"""

    async def execute(
        self,
        task_id: str,
        config: TaskConfig,
        progress_callback: Callable[[float, str, str], None],
        cancel_token: CancellationToken,
    ) -> ProcessingResult:
        from mediafactory.api.task_manager import (
            SimpleProgressAdapter,
        )  # 延迟导入避免环
        from mediafactory.services import (
            runner as runner_module,
        )  # 延迟导入，运行时查表

        fn = runner_module.RUNNERS.get(config.task_type)
        if fn is None:
            return ProcessingResult(
                success=False,
                error_message=f"No executor for task type: {config.task_type}",
                error_type="ConfigurationError",
            )
        adapter = SimpleProgressAdapter(progress_callback, cancel_token)
        return await fn(config, adapter)

    def cancel(self, task_id: str) -> None:
        pass  # 进程内取消走 TaskManager 的 token 路径

    def shutdown(self) -> None:
        pass


def _worker_main(cmd_q: Any, res_q: Any, cancel_event: Any) -> None:
    """子进程主循环：串行执行 run 命令，收到 None 优雅退出。"""
    while True:
        cmd = cmd_q.get()
        if cmd is None:
            break
        if cmd.get("cmd") != "run":
            continue
        task_id = cmd["task_id"]
        try:
            result = _run_task_in_worker(task_id, cmd["config"], res_q, cancel_event)
        except Exception as e:  # 兜底：投影函数自身出错也不让子进程崩
            result = {
                "success": False,
                "output_path": None,
                "error_message": str(e),
                "error_type": type(e).__name__,
                "metadata": {},
            }
        res_q.put({"kind": "result", "task_id": task_id, "result": result})


class WorkerProcessExecutor:
    """子进程执行器（生产）：任务下发 worker，进度/结果经 IPC 回传。

    串行执行（一次一个任务）；子进程崩溃只判当前任务失败，
    下一次 execute 自动重启子进程（崩溃隔离的核心）。
    """

    def __init__(self) -> None:
        self._ctx = mp.get_context("spawn")  # macOS/Windows 一致行为
        self._process: Optional[Any] = None
        self._cmd_q: Optional[Any] = None
        self._res_q: Optional[Any] = None
        self._cancel_event: Optional[Any] = None
        self._reader: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._pending: Dict[str, asyncio.Future] = {}
        self._progress_cb: Optional[Callable[[float, str, str], None]] = None
        self._running_task_id: Optional[str] = None
        self._shutting_down = False

    # ---- 生命周期 ----

    def _close_ipc(self) -> None:
        """回收队列/事件句柄，避免 respawn/shutdown 泄漏 POSIX 信号量。"""
        for obj in (self._cmd_q, self._res_q, self._cancel_event):
            if obj is not None:
                try:
                    obj.close()
                except Exception:
                    pass

    def _ensure_started(self) -> None:
        """确保子进程与读线程就绪；已死则重启（respawn）。"""
        if self._process is not None and self._process.is_alive():
            return
        # 旧子进程已死不会再写队列，close 旧句柄后再建新资源
        self._close_ipc()
        self._cmd_q = self._ctx.Queue()
        self._res_q = self._ctx.Queue()
        self._cancel_event = self._ctx.Event()
        self._process = self._ctx.Process(
            target=_worker_main,
            args=(self._cmd_q, self._res_q, self._cancel_event),
            daemon=True,
        )
        self._process.start()
        if self._reader is None or not self._reader.is_alive():
            self._reader = threading.Thread(
                target=self._read_results, daemon=True, name="worker-result-reader"
            )
            self._reader.start()

    def _read_results(self) -> None:
        """后台线程：把子进程消息派发回事件循环（进度直调、结果 resolve Future）。"""
        while not self._shutting_down:
            q = self._res_q
            if q is None:
                time.sleep(0.05)
                continue
            try:
                msg = q.get(timeout=0.5)
            except Exception:  # queue.Empty / 队列关闭，继续轮询
                continue
            try:
                kind = msg.get("kind")
                if kind == "progress" and self._progress_cb is not None:
                    cb = self._progress_cb
                    try:
                        cb(
                            msg["progress"],
                            msg.get("message", ""),
                            msg.get("stage") or "",
                        )
                    except Exception:
                        # 进度回调失败不影响执行，但留痕排查
                        logger.warning("进度回调抛错，已忽略", exc_info=True)
                elif kind == "result":
                    task_id = msg["task_id"]
                    fut = self._pending.get(task_id)
                    if fut is not None and not fut.done():
                        payload = msg["result"]
                        loop = self._loop
                        if loop is not None:
                            loop.call_soon_threadsafe(
                                lambda f=fut, p=payload: (
                                    None if f.done() else f.set_result(p)
                                )
                            )
            except Exception:
                # 单条消息派发失败不杀 reader 线程，留痕后继续
                logger.warning("worker 消息派发失败: %r", msg, exc_info=True)

    # ---- TaskExecutor 接口 ----

    async def execute(
        self,
        task_id: str,
        config: TaskConfig,
        progress_callback: Callable[[float, str, str], None],
        cancel_token: CancellationToken,
    ) -> ProcessingResult:
        if self._shutting_down:
            raise RuntimeError("WorkerProcessExecutor already shut down")
        self._ensure_started()
        loop = asyncio.get_running_loop()
        self._loop = loop
        fut: asyncio.Future = loop.create_future()
        self._pending[task_id] = fut
        self._progress_cb = progress_callback
        self._cancel_event.clear()  # 串行单任务：任务下发前清取消标志
        self._running_task_id = task_id
        self._cmd_q.put(
            {"cmd": "run", "task_id": task_id, "config": config.model_dump(mode="json")}
        )
        watchdog = asyncio.create_task(self._watchdog(fut))
        try:
            payload = await fut
            return ProcessingResult(
                success=payload["success"],
                output_path=payload.get("output_path"),
                error_message=payload.get("error_message", ""),
                error_type=payload.get("error_type"),
                metadata=payload.get("metadata") or {},
            )
        finally:
            watchdog.cancel()
            self._pending.pop(task_id, None)
            self._progress_cb = None
            self._running_task_id = None

    async def _watchdog(self, fut: asyncio.Future) -> None:
        """子进程死亡检测：当前任务判失败（不自动重试——产物可能不完整）。"""
        from mediafactory.i18n import t

        while True:
            await asyncio.sleep(0.1)
            if fut.done():
                return
            if self._process is not None and not self._process.is_alive():
                if not fut.done():
                    fut.set_result(
                        {
                            "success": False,
                            "output_path": None,
                            "error_message": t("task.workerCrashed"),
                            "error_type": "WorkerCrashedError",
                            "metadata": {},
                        }
                    )
                return

    def cancel(self, task_id: str) -> None:
        # 只取消当前运行的任务：错 id（如排队中任务）不得误杀运行中的任务
        if self._cancel_event is not None and task_id == self._running_task_id:
            self._cancel_event.set()

    def shutdown(self) -> None:
        """优雅停子进程（超时强杀），停读线程。"""
        self._shutting_down = True
        if self._process is not None and self._process.is_alive():
            try:
                self._cmd_q.put(None)
                self._process.join(timeout=5)
            except Exception:
                pass
            if self._process.is_alive():
                self._process.terminate()
                self._process.join(timeout=2)
        if self._reader is not None:
            self._reader.join(timeout=2)
        # 子进程与 reader 均已停止，回收队列/事件句柄
        self._close_ipc()
