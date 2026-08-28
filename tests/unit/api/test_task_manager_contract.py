"""task_manager 契约测试。

锁定任务状态机（PENDING→RUNNING→COMPLETED/FAILED/CANCELLED）、串行队列推进、
取消语义（队列移除、取消结果不被覆盖）、进度透传——
Phase 3 将重构这些区域，先锁行为。
"""

import asyncio

import pytest

from mediafactory.api.schemas import TaskConfig, TaskStatus, TaskType
from mediafactory.api.task_manager import TaskManager
from mediafactory.api.websocket import manager as ws_manager
from mediafactory.i18n import t
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


class TestTaskLifecycle:
    def test_execute_task_success_path(self, monkeypatch):
        async def scenario():
            manager = TaskManager()
            task_id = await manager.create_task(make_config())

            async def ok_executor(config, progress):
                progress.set_stage("audio_extraction")
                progress.update(10.0, "working")
                await asyncio.sleep(0)  # 让 call_soon_threadsafe 的调度得以执行
                return ProcessingResult(success=True, output_path="out.wav")

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

            async def bad_executor(config, progress):
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

    def test_execute_task_failed_result_marks_failed(self, monkeypatch):
        async def scenario():
            manager = TaskManager()
            task_id = await manager.create_task(make_config())

            async def fail_executor(config, progress):
                return ProcessingResult(
                    success=False,
                    error_message="boom",
                    error_type="ProcessingError",
                )

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

            async def cancelling_executor(config, progress):
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


class TestProgressPassthrough:
    """特征测试：锁定进度透传语义（区间映射职责已移至 Pipeline，
    见 tests/unit/pipeline/test_progress_mapping.py）。"""

    def test_progress_passthrough(self, monkeypatch):
        async def scenario():
            manager = TaskManager()
            task_id = await manager.create_task(make_config())

            async def executor(config, progress):
                progress.set_stage("anything")
                progress.update(42.0, "m")
                await asyncio.sleep(0)
                return ProcessingResult(success=True, output_path="x")

            await manager._execute_task(task_id, executor)
            await asyncio.sleep(0)

        rec = BroadcastRecorder(monkeypatch)
        asyncio.run(scenario())
        # task_manager 不再做数值映射：进度与 stage 原样透传
        assert any(
            abs(c["progress"] - 42.0) < 0.01 and c["stage"] == "anything"
            for c in rec.progress_calls
        )

    def test_download_stage_passthrough(self, monkeypatch):
        async def scenario():
            manager = TaskManager()
            task_id = await manager.create_task(make_config())

            async def executor(config, progress):
                progress.set_stage("download")
                progress.update(37.5, "msg")
                await asyncio.sleep(0)
                return ProcessingResult(success=True, output_path="x")

            await manager._execute_task(task_id, executor)
            await asyncio.sleep(0)

        rec = BroadcastRecorder(monkeypatch)
        asyncio.run(scenario())
        # download 进度不经 Pipeline（0-100 直传），必须原样透传
        # （Phase 3 下载一等化防回归点）
        assert any(
            abs(c["progress"] - 37.5) < 0.01 and c["stage"] == "download"
            for c in rec.progress_calls
        )


class TestCancelAndQueue:
    def test_cancel_pending_task_removes_from_queue(self, monkeypatch):
        calls = {"a.mp4": 0, "b.mp4": 0}

        async def slow_executor(config, progress):
            calls[config.input_path] += 1
            await asyncio.sleep(0.05)
            return ProcessingResult(success=True, output_path="x")

        monkeypatch.setattr(
            "mediafactory.services.runner.RUNNERS", {TaskType.AUDIO: slow_executor}
        )

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
        # B 的 runner 从未执行
        assert calls["a.mp4"] == 1
        assert calls["b.mp4"] == 0

    def test_cancel_running_task_result_does_not_override_cancelled(self, monkeypatch):
        async def polling_executor(config, progress):
            while not progress.is_cancelled():
                await asyncio.sleep(0.005)
            # 取消后仍返回 success=True —— 锁定"取消的结果不得被覆盖"不变量
            return ProcessingResult(success=True, output_path="should-not-apply")

        monkeypatch.setattr(
            "mediafactory.services.runner.RUNNERS", {TaskType.AUDIO: polling_executor}
        )

        async def scenario():
            manager = TaskManager()
            task_id = await manager.create_task(make_config())
            assert await manager.start_single_task(task_id) is True
            await asyncio.sleep(0.02)  # 确保 runner 正在运行中
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
        # runner 返回的 success 结果被丢弃，不得覆盖 CANCELLED 状态
        assert status["outputPath"] is None
        assert all(c["success"] is False for c in rec.complete_calls)

    def test_serial_queue_executes_tasks_one_after_another(self, monkeypatch):
        order = []

        async def shared_executor(config, progress):
            order.append("start")
            await asyncio.sleep(0.01)
            order.append("end")
            return ProcessingResult(success=True, output_path="x")

        monkeypatch.setattr(
            "mediafactory.services.runner.RUNNERS", {TaskType.AUDIO: shared_executor}
        )

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


# RUNNERS 注册表完备性断言在 tests/unit/services/test_runner_contract.py
# （TestRunnersRegistry）——task_manager 侧与 runner 侧逐字重复，保留一份。
