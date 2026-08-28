"""task_manager 契约测试。

锁定任务状态机（PENDING→RUNNING→COMPLETED/FAILED/CANCELLED）、串行队列推进、
取消语义（队列移除、取消结果不被覆盖）、STAGE_RANGES 进度映射——
Phase 3 将重构这些区域，先锁行为。
"""

import asyncio

import pytest

from mediafactory.api.schemas import TaskConfig, TaskStatus, TaskType
from mediafactory.api.task_manager import TaskManager
from mediafactory.api.websocket import manager as ws_manager
from mediafactory.i18n import t

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


class TestTaskLifecycle:
    def test_execute_task_success_path(self, monkeypatch):
        async def scenario():
            manager = TaskManager()
            task_id = await manager.create_task(make_config())

            async def ok_executor(config, progress_callback, cancel_token):
                progress_callback(10.0, "working", "audio_extraction")
                await asyncio.sleep(0)  # 让 call_soon_threadsafe 的调度得以执行
                return {"success": True, "output_path": "out.wav", "error": None}

            await manager._execute_task(task_id, ok_executor)
            await asyncio.sleep(0)
            return manager, task_id

        rec = BroadcastRecorder(monkeypatch)
        manager, task_id = asyncio.run(scenario())
        status = asyncio.run(manager.get_task_status(task_id))
        assert status["status"] == "completed"
        assert status["outputPath"] == "out.wav"
        # 完成广播恰好一次且 success=True
        assert len(rec.complete_calls) == 1
        assert rec.complete_calls[0]["success"] is True

    def test_execute_task_exception_marks_failed(self, monkeypatch):
        async def scenario():
            manager = TaskManager()
            task_id = await manager.create_task(make_config())

            async def bad_executor(config, progress_callback, cancel_token):
                raise RuntimeError("engine exploded")

            await manager._execute_task(task_id, bad_executor)
            return manager, task_id

        rec = BroadcastRecorder(monkeypatch)
        manager, task_id = asyncio.run(scenario())
        status = asyncio.run(manager.get_task_status(task_id))
        assert status["status"] == "failed"
        # 未知异常经 sanitize_error 脱敏为通用消息，原始信息仅写入日志
        assert status["error"] == t("error.generic.unexpected")
        assert "engine exploded" not in status["error"]
        assert rec.complete_calls[0]["success"] is False

    def test_execute_task_result_failure_dict_marks_failed(self, monkeypatch):
        async def scenario():
            manager = TaskManager()
            task_id = await manager.create_task(make_config())

            async def fail_executor(config, progress_callback, cancel_token):
                return {"success": False, "output_path": None, "error": "boom"}

            await manager._execute_task(task_id, fail_executor)
            return manager, task_id

        BroadcastRecorder(monkeypatch)
        manager, task_id = asyncio.run(scenario())
        status = asyncio.run(manager.get_task_status(task_id))
        assert status["status"] == "failed"
        assert status["error"] == "boom"

    def test_execute_task_cancelled_error_marks_cancelled(self, monkeypatch):
        async def scenario():
            manager = TaskManager()
            task_id = await manager.create_task(make_config())

            async def cancelling_executor(config, progress_callback, cancel_token):
                raise asyncio.CancelledError()

            await manager._execute_task(task_id, cancelling_executor)
            return manager, task_id

        rec = BroadcastRecorder(monkeypatch)
        manager, task_id = asyncio.run(scenario())
        status = asyncio.run(manager.get_task_status(task_id))
        assert status["status"] == "cancelled"
        assert status["error"] == t("task.cancelled")
        assert len(rec.complete_calls) == 1
        assert rec.complete_calls[0]["success"] is False


class TestStageRangeMapping:
    """特征测试：锁定 STAGE_RANGES 映射语义（Phase 3 将改其实现方式）。"""

    def test_translation_stage_maps_into_70_95_window(self, monkeypatch):
        async def scenario():
            manager = TaskManager()
            task_id = await manager.create_task(make_config())

            async def executor(config, progress_callback, cancel_token):
                progress_callback(50.0, "half", "translation")
                await asyncio.sleep(0)
                return {"success": True, "output_path": "x", "error": None}

            await manager._execute_task(task_id, executor)
            await asyncio.sleep(0)

        rec = BroadcastRecorder(monkeypatch)
        asyncio.run(scenario())
        # translation 50% → 70 + 50/100*(95-70) = 82.5
        assert any(
            abs(c["progress"] - 82.5) < 0.01 and c["stage"] == "translation"
            for c in rec.progress_calls
        )

    def test_download_stage_identity_mapping(self, monkeypatch):
        async def scenario():
            manager = TaskManager()
            task_id = await manager.create_task(make_config())

            async def executor(config, progress_callback, cancel_token):
                progress_callback(37.5, "msg", "download")
                await asyncio.sleep(0)
                return {"success": True, "output_path": "x", "error": None}

            await manager._execute_task(task_id, executor)
            await asyncio.sleep(0)

        rec = BroadcastRecorder(monkeypatch)
        asyncio.run(scenario())
        # download: (0, 100) → 恒等映射，进度原样透传（Phase 3 下载一等化防回归点）
        assert any(
            abs(c["progress"] - 37.5) < 0.01 and c["stage"] == "download"
            for c in rec.progress_calls
        )

    def test_unknown_stage_keeps_raw_progress(self, monkeypatch):
        async def scenario():
            manager = TaskManager()
            task_id = await manager.create_task(make_config())

            async def executor(config, progress_callback, cancel_token):
                progress_callback(42.0, "mystery", "not_a_known_stage")
                await asyncio.sleep(0)
                return {"success": True, "output_path": "x", "error": None}

            await manager._execute_task(task_id, executor)
            await asyncio.sleep(0)

        rec = BroadcastRecorder(monkeypatch)
        asyncio.run(scenario())
        assert any(
            abs(c["progress"] - 42.0) < 0.01 for c in rec.progress_calls
        )


class TestCancelAndQueue:
    def test_cancel_pending_task_removes_from_queue(self, monkeypatch):
        import mediafactory.api.task_executor as te

        calls = {"a.mp4": 0, "b.mp4": 0}

        async def slow_executor(config, progress_callback, cancel_token):
            calls[config.input_path] += 1
            await asyncio.sleep(0.05)
            return {"success": True, "output_path": "x", "error": None}

        monkeypatch.setattr(te, "TASK_EXECUTORS", {TaskType.AUDIO: slow_executor})

        async def scenario():
            manager = TaskManager()
            a_id = await manager.create_task(make_config("a.mp4"), name="A")
            assert await manager.start_single_task(a_id) is True
            # 等 A 真正进入 RUNNING（asyncio.create_task 需要一次循环调度）
            for _ in range(200):
                if manager._tasks[a_id].status == TaskStatus.RUNNING:
                    break
                await asyncio.sleep(0.005)

            b_id = await manager.create_task(make_config("b.mp4"), name="B")
            await manager.start_all_pending()  # A 在 RUNNING → B 仅入队等待
            assert b_id in manager._queue  # 前置：B 确实在队列中等待

            ok = await manager.cancel_task(b_id)

            # 等 A 跑完（慢 executor 约 0.05s）
            for _ in range(200):
                if manager._tasks[a_id].status == TaskStatus.COMPLETED:
                    break
                await asyncio.sleep(0.01)
            return manager, a_id, b_id, ok

        BroadcastRecorder(monkeypatch)
        manager, a_id, b_id, ok = asyncio.run(scenario())
        assert ok is True
        # B 已取消且从 _queue 移除（真正执行 remove 分支）
        status_b = asyncio.run(manager.get_task_status(b_id))
        assert status_b["status"] == "cancelled"
        assert b_id not in manager._queue
        # A 不受影响，正常完成
        status_a = asyncio.run(manager.get_task_status(a_id))
        assert status_a["status"] == "completed"
        # B 的 executor 从未执行
        assert calls["a.mp4"] == 1
        assert calls["b.mp4"] == 0

    def test_cancel_running_task_result_does_not_override_cancelled(self, monkeypatch):
        import mediafactory.api.task_executor as te

        async def polling_executor(config, progress_callback, cancel_token):
            while not cancel_token.is_cancelled():
                await asyncio.sleep(0.005)
            # 取消后仍返回 success=True —— 锁定"取消的结果不得被覆盖"不变量
            return {"success": True, "output_path": "should-not-apply", "error": None}

        monkeypatch.setattr(te, "TASK_EXECUTORS", {TaskType.AUDIO: polling_executor})

        async def scenario():
            manager = TaskManager()
            task_id = await manager.create_task(make_config())
            assert await manager.start_single_task(task_id) is True
            await asyncio.sleep(0.02)  # 确保 executor 正在运行中
            ok = await manager.cancel_task(task_id)
            # 等后台 _execute_task 收尾（completed_at 在 finally 中设置）
            for _ in range(200):
                if manager._tasks[task_id].completed_at is not None:
                    break
                await asyncio.sleep(0.01)
            return manager, task_id, ok

        rec = BroadcastRecorder(monkeypatch)
        manager, task_id, ok = asyncio.run(scenario())
        assert ok is True
        status = asyncio.run(manager.get_task_status(task_id))
        assert status["status"] == "cancelled"
        # executor 返回的 success 结果被丢弃，不得覆盖 CANCELLED 状态
        assert status["outputPath"] is None
        assert all(c["success"] is False for c in rec.complete_calls)

    def test_serial_queue_executes_tasks_one_after_another(self, monkeypatch):
        import mediafactory.api.task_executor as te

        order = []

        async def shared_executor(config, progress_callback, cancel_token):
            order.append("start")
            await asyncio.sleep(0.01)
            order.append("end")
            return {"success": True, "output_path": "x", "error": None}

        monkeypatch.setattr(te, "TASK_EXECUTORS", {TaskType.AUDIO: shared_executor})

        async def scenario():
            manager = TaskManager()
            t1 = await manager.create_task(make_config(), name="t1")
            t2 = await manager.create_task(make_config(), name="t2")
            await manager.start_all_pending()
            # 轮询等待后台 asyncio.create_task 完成（上限 2 秒）
            for _ in range(200):
                if all(
                    manager._tasks[tid].status == TaskStatus.COMPLETED
                    for tid in (t1, t2)
                ):
                    break
                await asyncio.sleep(0.01)
            else:
                pytest.fail("queue did not drain within 2s")
            return manager, (t1, t2)

        BroadcastRecorder(monkeypatch)
        manager, (t1, t2) = asyncio.run(scenario())
        s1 = asyncio.run(manager.get_task_status(t1))
        s2 = asyncio.run(manager.get_task_status(t2))
        assert s1["status"] == "completed"
        assert s2["status"] == "completed"
        # 串行语义：start/end 不得交错
        assert order == ["start", "end", "start", "end"]
