"""TaskManager 历史写入契约测试。

锁定三个终态写入点（执行完成/取消/外部状态更新）与故障隔离契约
（历史仓储抛异常时任务主流程不受影响）。
"""

import asyncio

import pytest

from mediafactory.api.schemas import TaskConfig, TaskResult, TaskStatus, TaskType
from mediafactory.api.task_manager import TaskManager
from mediafactory.api.websocket import manager as ws_manager
from mediafactory.persistence import HistoryRepository
from mediafactory.pipeline.context import ProcessingResult

pytestmark = [pytest.mark.unit]


class BroadcastRecorder:
    """记录 ws_manager 广播调用的替身（对齐既有测试模式）。"""

    def __init__(self, monkeypatch):
        monkeypatch.setattr(ws_manager, "broadcast_progress", self._noop_async)
        monkeypatch.setattr(ws_manager, "broadcast_task_complete", self._noop_async)

    async def _noop_async(self, *args, **kwargs):
        return None


def make_config() -> TaskConfig:
    return TaskConfig(task_type=TaskType.AUDIO, input_path="v.mp4")


class TestTerminalStateWritesHistory:
    def test_success_writes_history(self, monkeypatch):
        BroadcastRecorder(monkeypatch)

        async def scenario():
            repo = HistoryRepository()
            manager = TaskManager(history_repo=repo)
            task_id = await manager.create_task(make_config())

            async def ok_executor(config, progress):
                return ProcessingResult(success=True, output_path="out.wav")

            await manager._execute_task(task_id, ok_executor)
            await asyncio.sleep(0)
            return repo, task_id

        repo, task_id = asyncio.run(scenario())
        entry = asyncio.run(repo.get_record(task_id))
        assert entry is not None
        assert entry.status == "completed"
        assert entry.output_path == "out.wav"
        assert entry.started_at is not None

    def test_failure_writes_history(self, monkeypatch):
        BroadcastRecorder(monkeypatch)

        async def scenario():
            repo = HistoryRepository()
            manager = TaskManager(history_repo=repo)
            task_id = await manager.create_task(make_config())

            async def fail_executor(config, progress):
                return ProcessingResult(
                    success=False, error_message="exp", error_type="ProcessingError"
                )

            await manager._execute_task(task_id, fail_executor)
            await asyncio.sleep(0)
            return repo, task_id

        repo, task_id = asyncio.run(scenario())
        entry = asyncio.run(repo.get_record(task_id))
        assert entry is not None
        assert entry.status == "failed"
        assert entry.error_type == "ProcessingError"

    def test_cancel_writes_history(self, monkeypatch):
        """排队中取消（不经过 _execute_task）也写历史"""
        BroadcastRecorder(monkeypatch)

        async def scenario():
            repo = HistoryRepository()
            manager = TaskManager(history_repo=repo)
            task_id = await manager.create_task(make_config())
            ok = await manager.cancel_task(task_id)
            return repo, task_id, ok

        repo, task_id, ok = asyncio.run(scenario())
        assert ok is True
        entry = asyncio.run(repo.get_record(task_id))
        assert entry is not None
        assert entry.status == "cancelled"

    def test_update_task_status_terminal_writes_history(self, monkeypatch):
        """外部状态更新（下载任务路径）的终态写历史"""
        BroadcastRecorder(monkeypatch)

        async def scenario():
            repo = HistoryRepository()
            manager = TaskManager(history_repo=repo)
            task_id = await manager.create_task(make_config())
            await manager.update_task_status(
                task_id,
                status=TaskStatus.FAILED,
                result=TaskResult(
                    task_id=task_id,
                    success=False,
                    error="dl",
                    error_type="DownloadError",
                ),
            )
            return repo, task_id

        repo, task_id = asyncio.run(scenario())
        entry = asyncio.run(repo.get_record(task_id))
        assert entry is not None
        assert entry.status == "failed"

    def test_non_terminal_status_does_not_write(self, monkeypatch):
        BroadcastRecorder(monkeypatch)

        async def scenario():
            repo = HistoryRepository()
            manager = TaskManager(history_repo=repo)
            task_id = await manager.create_task(make_config())
            await manager.update_task_status(task_id, status=TaskStatus.RUNNING)
            _, total = await repo.list_records()
            return total

        assert asyncio.run(scenario()) == 0


class TestHistoryFailureIsolation:
    def test_repo_exception_does_not_break_task(self, monkeypatch):
        """故障隔离契约：历史仓储抛异常 → 任务仍正常完成"""

        class ExplodingRepo:
            async def upsert(self, entry):
                raise RuntimeError("history db down")

        BroadcastRecorder(monkeypatch)

        async def scenario():
            manager = TaskManager(history_repo=ExplodingRepo())
            task_id = await manager.create_task(make_config())

            async def ok_executor(config, progress):
                return ProcessingResult(success=True, output_path="out.wav")

            await manager._execute_task(task_id, ok_executor)
            await asyncio.sleep(0)
            return await manager.get_task_status(task_id)

        status = asyncio.run(scenario())
        assert status["status"] == "completed"

    def test_no_repo_is_noop(self, monkeypatch):
        """history_repo=None（旧装配）不写历史也不报错"""
        BroadcastRecorder(monkeypatch)

        async def scenario():
            manager = TaskManager()  # 无历史仓储
            task_id = await manager.create_task(make_config())

            async def ok_executor(config, progress):
                return ProcessingResult(success=True, output_path="out.wav")

            await manager._execute_task(task_id, ok_executor)
            await asyncio.sleep(0)
            return True

        assert asyncio.run(scenario()) is True
