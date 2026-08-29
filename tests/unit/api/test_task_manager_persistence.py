"""TaskManager 持久化与重启恢复测试。

BroadcastRecorder 与 make_config 复制自 test_task_manager_contract.py
（测试模块间不互相导入，保持各自独立可跑）。
"""

import asyncio

import pytest

from mediafactory.api.schemas import TaskConfig, TaskStatus, TaskType
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


class TestQueuePersistence:
    def test_cancel_queued_task_persists(self, tmp_path, monkeypatch):
        async def scenario():
            manager = TaskManager(db_path=tmp_path / "tasks.db")

            async def hang_executor(config, progress):
                await asyncio.sleep(30)  # 卡住 A，让 B 留在队列

            monkeypatch.setattr(
                "mediafactory.services.runner.RUNNERS", {TaskType.AUDIO: hang_executor}
            )
            a_id = await manager.create_task(make_config("a.mp4"), name="A")
            await manager.start_single_task(a_id)
            b_id = await manager.create_task(make_config("b.mp4"), name="B")
            await manager.start_all_pending()
            assert (
                manager._store.get(b_id)["queued_at"] is not None
            )  # 前置：B 确实已入队
            await manager.cancel_task(b_id)
            await manager.shutdown()
            return manager, a_id, b_id

        BroadcastRecorder(monkeypatch)
        manager, a_id, b_id = asyncio.run(scenario())
        row_b = manager._store.get(b_id)
        assert row_b["status"] == "cancelled"
        assert row_b["queued_at"] is None  # 已出队

    def test_remove_task_deletes_row(self, tmp_path):
        async def scenario():
            manager = TaskManager(db_path=tmp_path / "tasks.db")
            task_id = await manager.create_task(make_config())
            assert await manager.remove_task(task_id) == "removed"
            return manager, task_id

        manager, task_id = asyncio.run(scenario())
        assert manager._store.get(task_id) is None

    def test_update_task_config_persists(self, tmp_path):
        async def scenario():
            manager = TaskManager(db_path=tmp_path / "tasks.db")
            task_id = await manager.create_task(make_config())
            ok = await manager.update_task_config(task_id, {"output_format": "ass"})
            return manager, task_id, ok

        manager, task_id, ok = asyncio.run(scenario())
        assert ok is True
        # model_dump_json 为紧凑输出（无冒号后空格）
        assert '"output_format":"ass"' in manager._store.get(task_id)["config_json"]

    def test_retry_task_persists_reset_and_requeue(self, tmp_path, monkeypatch):
        async def scenario():
            manager = TaskManager(db_path=tmp_path / "tasks.db")

            async def hang_executor(config, progress):
                await asyncio.sleep(30)  # 卡住 A，让 B 重试后留在队列

            async def fail_executor(config, progress):
                return ProcessingResult(
                    success=False, error_message="boom", error_type="ProcessingError"
                )

            monkeypatch.setattr(
                "mediafactory.services.runner.RUNNERS", {TaskType.AUDIO: hang_executor}
            )
            a_id = await manager.create_task(make_config("a.mp4"), name="A")
            await manager.start_single_task(a_id)  # 占住运行位
            b_id = await manager.create_task(make_config("b.mp4"), name="B")
            await manager._execute_task(b_id, fail_executor)  # 直接跑失败路径
            ok = await manager.retry_task(b_id)
            # scenario 内快照行数据（避免 teardown 时序影响断言）
            row = manager._store.get(b_id)
            await manager.shutdown()  # 清队列，避免 teardown 留下悬挂后台任务
            return ok, row

        BroadcastRecorder(monkeypatch)
        ok, row = asyncio.run(scenario())
        assert ok is True
        assert row["status"] == "pending"
        assert row["queued_at"] is not None  # 重新入队
        assert row["error"] is None  # 旧失败已清

    def test_update_task_status_persists(self, tmp_path):
        async def scenario():
            manager = TaskManager(db_path=tmp_path / "tasks.db")
            task_id = await manager.create_task(make_config())
            ok = await manager.update_task_status(task_id, TaskStatus.FAILED)
            return manager, task_id, ok

        manager, task_id, ok = asyncio.run(scenario())
        assert ok is True
        assert manager._store.get(task_id)["status"] == "failed"
