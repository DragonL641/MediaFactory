"""TaskManager 持久化与重启恢复测试。

BroadcastRecorder 与 make_config 复制自 test_task_manager_contract.py
（测试模块间不互相导入，保持各自独立可跑）。
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


class TestRestartRecovery:
    # 崩溃协程的 keepalive：进程级持有引用，阻止 GC 事后跑其 finally
    # （finally 会对旧连接写库，连接被回收时产生 unraisable 告警噪音）
    _crashed_keepalive: list = []

    def test_running_marked_failed_and_queue_rebuilt(self, tmp_path, monkeypatch):
        db = tmp_path / "tasks.db"

        async def seed():
            # 模拟旧 daemon：R 卡在 RUNNING（hang executor 永不返回）
            manager = TaskManager(db_path=db)

            async def hang_executor(config, progress):
                await asyncio.sleep(30)

            monkeypatch.setattr(
                "mediafactory.services.runner.RUNNERS", {TaskType.AUDIO: hang_executor}
            )
            run_id = await manager.create_task(make_config("run.mp4"), name="R")
            await manager.start_single_task(run_id)  # R → RUNNING
            for _ in range(200):
                if manager._tasks[run_id].status.value == "running":
                    break
                await asyncio.sleep(0.005)
            # 再造一行 RUNNING 残留：批量分支在 manager 完整链路同样成立
            run2_id = await manager.create_task(make_config("run2.mp4"), name="R2")
            await manager.update_task_status(run2_id, TaskStatus.RUNNING)
            q_id = await manager.create_task(make_config("q.mp4"), name="Q")
            await manager.start_all_pending()  # R 在 RUNNING → Q 仅入队
            return manager, run_id, run2_id, q_id

        BroadcastRecorder(monkeypatch)
        # 手动建循环后直接 close，模拟进程崩溃（挂起协程被原样丢弃）。
        # 不能用 asyncio.run：它关闭时会 cancel 后台协程并跑完 CancelledError/
        # finally 清理，把 R 落成 cancelled、Q 拉起成 running，留不下 RUNNING 残留。
        loop = asyncio.new_event_loop()
        try:
            manager, run_id, run2_id, q_id = loop.run_until_complete(seed())
            # 崩溃协程进程级持有：测试结束后 GC 也不得跑其 finally 改写 DB
            crashed = [t for t in asyncio.all_tasks(loop) if not t.done()]
            self._crashed_keepalive.extend(crashed)
        finally:
            loop.close()
        assert crashed, "seed 未留下崩溃协程"

        # 新 daemon 挂同一 db 恢复
        manager2 = TaskManager(db_path=db)
        asyncio.run(manager2.recover())
        s_run = asyncio.run(manager2.get_task_status(run_id))
        s_run2 = asyncio.run(manager2.get_task_status(run2_id))
        s_q = asyncio.run(manager2.get_task_status(q_id))
        assert s_run["status"] == "failed"  # worker 死掉的 RUNNING 判失败
        # 恢复错误消息的回读路径：recover 写入 → _load_from_store 构造
        # TaskResult → get_task_status()["error"]（用 t() 镜像实现，跟随 locale）
        assert s_run["error"] == t("task.interruptedByRestart")
        assert s_run2["status"] == "failed"  # 批量：多行 RUNNING 残留一并标 FAILED
        assert s_q["status"] == "pending"  # 队列任务保留
        assert q_id in manager2._queue  # 队列按 queued_at 重建
        assert run_id not in manager2._queue

    def test_recover_with_clean_store_is_noop(self, tmp_path):
        async def scenario():
            manager = TaskManager(db_path=tmp_path / "tasks.db")
            await manager.recover()
            return manager

        manager = asyncio.run(scenario())
        assert manager._tasks == {}
        assert manager._queue == []

    def test_corrupt_row_skipped_others_recovered(self, tmp_path):
        # 坏行（过期/损坏的 config_json）只跳过告警，不阻断 recover；
        # 坏行即便带 queued 标记也不得混入重建后的队列
        db = tmp_path / "tasks.db"
        manager = TaskManager(db_path=db)

        async def seed():
            good_id = await manager.create_task(make_config("good.mp4"), name="G")
            bad_id = await manager.create_task(make_config(), name="Bad")
            return good_id, bad_id

        good_id, bad_id = asyncio.run(seed())
        manager._store.set_queued(good_id, True)
        manager._store.set_queued(bad_id, True)
        # 模拟坏行：旧版本/损坏的 config 结构（model_validate_json 必失败）
        manager._store.update(bad_id, config_json='{"stale_schema": true}')

        manager2 = TaskManager(db_path=db)
        asyncio.run(manager2.recover())  # 不抛异常即通过恢复链路
        assert good_id in manager2._tasks
        assert bad_id not in manager2._tasks
        assert good_id in manager2._queue
        assert bad_id not in manager2._queue


class TestProductionWiring:
    def test_get_task_manager_uses_worker_executor(self, tmp_path, monkeypatch):
        import mediafactory.api.task_manager as tm_module
        from mediafactory.api.worker import WorkerProcessExecutor

        # get_data_root_dir 基于 __file__ 解析（与 CWD 无关），patch 到 tmp_path
        # 使 data/tasks.db 落临时目录，不在仓库根产生真实文件
        monkeypatch.setattr("mediafactory.config.get_data_root_dir", lambda: tmp_path)
        monkeypatch.setattr(tm_module, "_task_manager", None)
        manager = tm_module.get_task_manager()
        assert isinstance(manager._executor, WorkerProcessExecutor)
        assert (tmp_path / "data" / "tasks.db").exists()


class TestLifespanWiring:
    def test_lifespan_runs_recover_on_startup(self, monkeypatch, tmp_path):
        # 冒烟：真实 FastAPI lifespan 启动会调用单例的 recover()
        # main.py 以 `from ... import get_task_manager` 绑定名字，
        # 打桩 main 模块属性即可让 lifespan 用注入的 manager
        from fastapi.testclient import TestClient

        import mediafactory.api.main as main_module

        manager = TaskManager(db_path=tmp_path / "tasks.db")
        monkeypatch.setattr(main_module, "get_task_manager", lambda: manager)

        calls = []

        async def fake_recover():
            calls.append("recover")

        monkeypatch.setattr(manager, "recover", fake_recover)

        with TestClient(main_module.get_app()):
            pass  # startup 阶段应触发 recover

        assert calls == ["recover"]


class TestEndToEndWithWorker:
    def test_full_chain_through_worker_subprocess(self, tmp_path, monkeypatch):
        from mediafactory.api.worker import WorkerProcessExecutor

        rec = BroadcastRecorder(monkeypatch)

        async def scenario():
            manager = TaskManager(
                db_path=tmp_path / "tasks.db", executor=WorkerProcessExecutor()
            )
            config = TaskConfig(
                task_type=TaskType.AUDIO, input_path="/nonexistent/x.wav"
            )
            task_id = await manager.create_task(config)
            await manager.start_all_pending()
            for _ in range(400):  # 上限 8 秒（spawn + 模块导入）
                status = await manager.get_task_status(task_id)
                if status["status"] in ("failed", "completed"):
                    break
                await asyncio.sleep(0.02)
            await manager.shutdown()  # 收尾：停子进程
            return manager, task_id, status

        manager, task_id, status = asyncio.run(scenario())
        assert status["status"] == "failed"  # 真实 run_audio 对缺失输入快速失败
        assert any(c["success"] is False for c in rec.complete_calls)
        # 终态已落库
        row = manager._store.get(task_id)
        assert row["status"] == "failed"
