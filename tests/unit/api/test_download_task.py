"""download_task 契约测试。

锁定 start_download 后台执行语义：任务创建后立即 fire-and-forget 执行（不进任务队列）、
成功/失败状态流转、on_complete 仅在成功时触发一次、active_downloads 并发保护集合的
加/清时机，以及 sync_progress 的 500ms 节流 + >=0.99 直通规则。
全部 mock（download_model / task_manager / ws 广播），不碰真实网络与 HuggingFace。
"""

import asyncio

import pytest

import mediafactory.api.download_task as download_task_module
import mediafactory.models.model_download as model_download_module
from mediafactory.api.download_task import (
    _execute_download_task,
    active_downloads,
    start_download,
)
from mediafactory.api.schemas import TaskConfig, TaskStatus, TaskType
from mediafactory.api.task_manager import TaskManager
from mediafactory.api.websocket import manager as ws_manager

pytestmark = [pytest.mark.unit]

_TERMINAL_STATUSES = (
    TaskStatus.COMPLETED,
    TaskStatus.FAILED,
    TaskStatus.CANCELLED,
)


class BroadcastRecorder:
    """记录 ws_manager 广播调用的替身（同 test_task_manager_contract 模式）。"""

    def __init__(self, monkeypatch):
        self.progress_calls = []
        self.complete_calls = []
        monkeypatch.setattr(ws_manager, "broadcast_progress", self._progress)
        monkeypatch.setattr(ws_manager, "broadcast_task_complete", self._complete)

    async def _progress(self, *args, **kwargs):
        self.progress_calls.append(kwargs)

    async def _complete(self, *args, **kwargs):
        self.complete_calls.append(kwargs)


@pytest.fixture(autouse=True)
def clean_active_downloads():
    """隔离模块级并发下载集合，避免测试间及失败后互相污染。"""
    download_task_module._active_downloads.clear()
    yield
    download_task_module._active_downloads.clear()


async def wait_until_finished(manager: TaskManager, task_id: str, model_id: str):
    """轮询等待 fire-and-forget 下载任务到达终态且并发保护集合已清空（上限 2s）。

    _active_downloads.discard 是后台协程 finally 的最后一条语句，
    集合清空即可保证 on_complete / 完成广播均已执行完毕。
    """
    for _ in range(200):
        status = manager._tasks[task_id].status
        if (
            status in _TERMINAL_STATUSES
            and model_id not in download_task_module._active_downloads
        ):
            return status
        await asyncio.sleep(0.01)
    pytest.fail("download task did not finish within 2s")


class TestStartDownload:
    def test_start_download_success_path(self, monkeypatch):
        download_calls = []

        def fake_download_model(*args, **kwargs):
            download_calls.append({"args": args, "kwargs": kwargs})
            return "models/org/model"  # 假路径，立即返回，不碰网络

        manager = TaskManager()
        monkeypatch.setattr(
            "mediafactory.api.download_task.get_task_manager", lambda: manager
        )
        monkeypatch.setattr(
            model_download_module, "download_model", fake_download_model
        )

        on_complete_calls = []

        async def scenario():
            task_id = await start_download(
                "org/model", None, on_complete=lambda: on_complete_calls.append(1)
            )
            await wait_until_finished(manager, task_id, "org/model")
            return task_id

        rec = BroadcastRecorder(monkeypatch)
        task_id = asyncio.run(scenario())

        # 任务经独立 TaskManager 创建并到达 COMPLETED
        assert manager._tasks[task_id].status == TaskStatus.COMPLETED
        assert manager._tasks[task_id].config.task_type == TaskType.DOWNLOAD
        # download_model 收到 model_id（位置参数）与 download_source=None（官方源）
        assert len(download_calls) == 1
        assert download_calls[0]["args"] == ("org/model",)
        assert download_calls[0]["kwargs"]["download_source"] is None
        assert callable(download_calls[0]["kwargs"]["progress_callback"])
        # on_complete 恰好一次
        assert len(on_complete_calls) == 1
        # 完成后并发保护集合清空
        assert active_downloads() == set()
        # 完成广播恰好一次且 success=True
        assert len(rec.complete_calls) == 1
        assert rec.complete_calls[0]["success"] is True

    def test_start_download_failure_marks_failed(self, monkeypatch):
        def failing_download_model(*args, **kwargs):
            raise RuntimeError("network unreachable")

        manager = TaskManager()
        monkeypatch.setattr(
            "mediafactory.api.download_task.get_task_manager", lambda: manager
        )
        monkeypatch.setattr(
            model_download_module, "download_model", failing_download_model
        )

        on_complete_calls = []

        async def scenario():
            task_id = await start_download(
                "org/model", None, on_complete=lambda: on_complete_calls.append(1)
            )
            await wait_until_finished(manager, task_id, "org/model")
            return task_id

        rec = BroadcastRecorder(monkeypatch)
        task_id = asyncio.run(scenario())

        # 下载失败：任务标记 FAILED，on_complete 不触发，保护集合仍清空
        assert manager._tasks[task_id].status == TaskStatus.FAILED
        assert on_complete_calls == []
        assert active_downloads() == set()
        assert len(rec.complete_calls) == 1
        assert rec.complete_calls[0]["success"] is False


class TestProgressThrottle:
    def test_execute_download_task_progress_throttle(self, monkeypatch):
        def fake_download_model(model_id, download_source=None, progress_callback=None):
            # 同一时刻（远小于 500ms 窗口）连续触发 4 次：
            # 首个 0.1 必放行（_last_progress_time 初始为 0），
            # 随后两个 0.1 被节流吞掉，0.995 因 >=0.99 直通
            progress_callback(0.1, "m")
            progress_callback(0.1, "m")
            progress_callback(0.1, "m")
            progress_callback(0.995, "m")
            return "models/org/model"

        manager = TaskManager()
        monkeypatch.setattr(
            "mediafactory.api.download_task.get_task_manager", lambda: manager
        )
        monkeypatch.setattr(
            model_download_module, "download_model", fake_download_model
        )

        async def scenario():
            config = TaskConfig(task_type=TaskType.DOWNLOAD, input_path="org/model")
            task_id = await manager.create_task(config)
            await _execute_download_task(task_id, "org/model", None, None)
            # 留出事件循环时间，让 call_soon_threadsafe 调度的
            # _progress_callback 任务在 asyncio.run 收尾前执行完毕
            await asyncio.sleep(0.05)
            return task_id

        rec = BroadcastRecorder(monkeypatch)
        task_id = asyncio.run(scenario())

        # 4 次回调仅 2 次送达广播：首个 0.1（放行）+ 0.995（直通）
        assert len(rec.progress_calls) == 2
        progresses = sorted(c["progress"] for c in rec.progress_calls)
        assert abs(progresses[0] - 10.0) < 0.01  # 0.1 * 100，节流后放行的首个
        assert abs(progresses[1] - 99.5) < 0.01  # 0.995 * 100，>=0.99 直通
        assert all(c["stage"] == "download" for c in rec.progress_calls)
        # 直通任务本身正常完成
        assert manager._tasks[task_id].status == TaskStatus.COMPLETED
