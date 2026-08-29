"""worker 子进程侧与执行器单元测试。

真实 spawn 子进程的测试（TestWorkerProcessExecutor）每个约 1-3 秒
（子进程启动 + 模块导入），属可接受的 unit 慢测试。
"""

import asyncio
import threading
from types import SimpleNamespace

import pytest

from mediafactory.api.schemas import TaskConfig, TaskType
from mediafactory.api.worker import _WorkerProgress, _run_task_in_worker
from mediafactory.core.tool import CancellationToken

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
        result = _run_task_in_worker(
            "t1",
            missing_audio_config().model_dump(mode="json"),
            lambda msg: None,
            threading.Event(),
        )
        assert result["success"] is False
        assert result["error_message"]  # 非空的用户可读消息
        assert result["error_type"]
