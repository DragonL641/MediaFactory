"""worker 子进程与执行器接缝。

ML 重活在与 daemon 隔离的子进程中执行：
- 子进程崩溃（段错误等）只导致当前任务 FAILED，daemon 与队列存活
- 进度/结果经 multiprocessing.Queue 回传（纯 dict，无 live 引用）
- 取消经 multiprocessing.Event（协作式，任务在检查点停下）

TaskManager 经 TaskExecutor 接缝调用：
- InlineExecutor：进程内执行（默认；测试与 RUNNERS monkeypatch 路径）
- WorkerProcessExecutor：子进程执行（生产装配，Task 5 实现）
"""

import asyncio
from typing import Any, Callable, Dict, Optional

from mediafactory.api.schemas import TaskConfig
from mediafactory.pipeline.context import ProcessingResult

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
