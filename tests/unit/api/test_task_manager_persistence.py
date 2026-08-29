"""TaskManager 持久化与重启恢复测试。

BroadcastRecorder 与 make_config 复制自 test_task_manager_contract.py
（测试模块间不互相导入，保持各自独立可跑）。
"""

import asyncio

import pytest

from mediafactory.api.schemas import TaskConfig, TaskType
from mediafactory.api.task_manager import TaskManager
from mediafactory.api.websocket import manager as ws_manager
from mediafactory.pipeline.context import ProcessingResult

pytestmark = [pytest.mark.unit]


class BroadcastRecorder:
    """记录 ws_manager 广播调用的替身。"""

    def __init__(self, monkeypatch):
        self.progress_calls = []
        self.complete_calls = []
        monkeypatch.setattr(ws_manager, "broadcast_progress", self._progress)
        monkeypatch.setattr(ws_manager, "broadcast_task_complete", self._complete)

    async def _progress(self, *args, **kwargs):
        self.progress_calls.append(kwargs)

    async def _complete(self, *args, **kwargs):
        self.complete_calls.append(kwargs)


def make_config(input_path: str = "v.mp4") -> TaskConfig:
    return TaskConfig(task_type=TaskType.AUDIO, input_path=input_path)


class TestWriteThrough:
    def test_created_task_row_in_store(self, tmp_path):
        async def scenario():
            manager = TaskManager(db_path=tmp_path / "tasks.db")
            return manager, await manager.create_task(make_config(), name="My Task")

        manager, task_id = asyncio.run(scenario())
        row = manager._store.get(task_id)
        assert row is not None
        assert row["name"] == "My Task"
        assert row["status"] == "pending"
        assert '"task_type":"audio"' in row["config_json"]

    def test_completed_state_survives_restart(self, tmp_path, monkeypatch):
        db = tmp_path / "tasks.db"

        async def run_first():
            manager = TaskManager(db_path=db)
            task_id = await manager.create_task(make_config())

            async def ok_executor(config, progress):
                progress.set_stage("audio_extraction")
                progress.update(10.0, "working")
                await asyncio.sleep(0)
                return ProcessingResult(success=True, output_path="out.wav")

            await manager._execute_task(task_id, ok_executor)
            return task_id

        BroadcastRecorder(monkeypatch)
        task_id = asyncio.run(run_first())

        # 模拟重启：新 manager 挂同一 db，recover 后状态可见
        manager2 = TaskManager(db_path=db)
        asyncio.run(manager2.recover())
        status = asyncio.run(manager2.get_task_status(task_id))
        assert status["status"] == "completed"
        assert status["outputPath"] == "out.wav"

    def test_failed_state_survives_restart(self, tmp_path, monkeypatch):
        db = tmp_path / "tasks.db"

        async def run_first():
            manager = TaskManager(db_path=db)
            task_id = await manager.create_task(make_config())

            async def fail_executor(config, progress):
                return ProcessingResult(
                    success=False, error_message="boom", error_type="ProcessingError"
                )

            await manager._execute_task(task_id, fail_executor)
            return task_id

        BroadcastRecorder(monkeypatch)
        task_id = asyncio.run(run_first())

        manager2 = TaskManager(db_path=db)
        asyncio.run(manager2.recover())
        status = asyncio.run(manager2.get_task_status(task_id))
        assert status["status"] == "failed"
        assert status["error"] == "boom"
