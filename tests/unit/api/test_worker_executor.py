"""worker 子进程侧与执行器单元测试。

真实 spawn 子进程的测试（TestWorkerProcessExecutor）每个约 1-3 秒
（子进程启动 + 模块导入），属可接受的 unit 慢测试。
"""

import asyncio
import threading
from types import SimpleNamespace

import pytest

from mediafactory.api.schemas import TaskConfig, TaskType
from mediafactory.api.worker import (
    InlineExecutor,
    WorkerProcessExecutor,
    _WorkerProgress,
    _run_task_in_worker,
)
from mediafactory.core.tool import CancellationToken
from mediafactory.pipeline.context import ProcessingResult

pytestmark = [pytest.mark.unit]


def missing_audio_config() -> TaskConfig:
    # 不存在的输入文件：run_audio 直调引擎路径快速失败，无需 ML 模型
    return TaskConfig(
        task_type=TaskType.AUDIO, input_path="/nonexistent/definitely-missing.wav"
    )


class TestWorkerProgress:
    def test_update_forwards_message_shape(self):
        sink = []
        # res_q 契约是 put 接口（生产为 mp.Queue），测试用 list 承接的桩
        progress = _WorkerProgress(
            "t1", SimpleNamespace(put=sink.append), threading.Event()
        )
        progress.set_stage("transcription")
        progress.update(42.0, "msg")
        assert sink == [
            {
                "kind": "progress",
                "task_id": "t1",
                "progress": 42.0,
                "message": "msg",
                "stage": "transcription",
            }
        ]

    def test_update_suppressed_after_cancel(self):
        sink = []
        event = threading.Event()
        progress = _WorkerProgress("t1", SimpleNamespace(put=sink.append), event)
        event.set()
        progress.update(1.0, "m")
        assert progress.is_cancelled() is True
        assert sink == []


class TestRunTaskInWorker:
    def test_projects_failed_result_for_missing_input(self):
        # 进程内直接调用子进程侧函数：验证 RUNNERS 查表 + 异常转用户消息投影
        # res_q 用满足 put 契约的桩（与 _WorkerProgress 的接口约定一致）
        result = _run_task_in_worker(
            "t1",
            missing_audio_config().model_dump(mode="json"),
            SimpleNamespace(put=lambda m: None),
            threading.Event(),
        )
        assert result["success"] is False
        assert result["error_message"]  # 非空的用户可读消息
        assert result["error_type"]


class TestInlineExecutor:
    def test_dispatches_via_runners_registry(self, monkeypatch):
        seen = {}

        async def fake_runner(config, progress):
            seen["input"] = config.input_path
            progress.set_stage("audio_extraction")
            progress.update(5.0, "go")
            return ProcessingResult(success=True, output_path="ok.wav")

        monkeypatch.setattr(
            "mediafactory.services.runner.RUNNERS", {TaskType.AUDIO: fake_runner}
        )
        result = asyncio.run(
            InlineExecutor().execute(
                "t1", missing_audio_config(), lambda p, m, s: None, CancellationToken()
            )
        )
        assert result.success is True
        assert result.output_path == "ok.wav"
        assert seen["input"] == "/nonexistent/definitely-missing.wav"

    def test_unknown_type_returns_configuration_error(self):
        config = TaskConfig(
            task_type=TaskType.DOWNLOAD, input_path="m"
        )  # DOWNLOAD 无注册
        result = asyncio.run(
            InlineExecutor().execute(
                "t1", config, lambda p, m, s: None, CancellationToken()
            )
        )
        assert result.success is False
        assert result.error_type == "ConfigurationError"


class TestWorkerProcessExecutor:
    def test_execute_roundtrip_real_runner(self):
        # 真实 spawn 子进程跑 run_audio（缺失输入 → 快速失败），验证全链路：
        # 下发 → 子进程 RUNNERS 查表 → 异常转用户消息 → 结果投影回传
        executor = WorkerProcessExecutor()

        async def scenario():
            return await executor.execute(
                "t1", missing_audio_config(), lambda p, m, s: None, CancellationToken()
            )

        result = asyncio.run(scenario())
        executor.shutdown()
        assert result.success is False
        assert result.error_type != "WorkerCrashedError"  # 正常失败路径，非崩溃
        assert result.error_message
