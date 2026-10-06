"""GET /api/processing/tasks/{id}/logs 契约（FakeManager 隔离，不碰真 tasks.db）"""

import pytest
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.unit]


class FakeManager:
    """状态可注入的轻量 manager 替身"""

    def __init__(self):
        from mediafactory.api.schemas import TaskConfig, TaskStatus, TaskType

        self._tasks = {
            "task-1": type(
                "T",
                (),
                {
                    "config": TaskConfig(
                        task_type=TaskType.ENHANCE, input_path="/tmp/x.mp4"
                    ),
                    "status": TaskStatus.PENDING,
                },
            )()
        }


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr("mediafactory.config.get_data_root_dir", lambda: tmp_path)
    fake = FakeManager()

    from mediafactory.api.routes import processing as processing_routes

    monkeypatch.setattr(processing_routes, "_get_task_manager", lambda: fake)
    from mediafactory.api.main import get_app

    with TestClient(get_app()) as c:
        yield c


class TestTaskLogsEndpoint:
    def test_missing_file_returns_empty_lines(self, client):
        resp = client.get("/api/processing/tasks/task-1/logs")
        assert resp.status_code == 200
        assert resp.json() == {"taskId": "task-1", "running": False, "lines": []}

    def test_written_log_returned_as_tail(self, client, tmp_path):
        from mediafactory.api.task_logger import task_log_path

        task_log_path("task-1").write_text("l1\nl2\nl3\n", encoding="utf-8")
        resp = client.get("/api/processing/tasks/task-1/logs")
        assert resp.json()["lines"] == ["l1", "l2", "l3"]

    def test_unknown_task_404(self, client):
        assert client.get("/api/processing/tasks/nope/logs").status_code == 404

    def test_cleanup_task_log_idempotent(self, tmp_path, monkeypatch):
        monkeypatch.setattr("mediafactory.config.get_data_root_dir", lambda: tmp_path)
        from mediafactory.api.task_logger import cleanup_task_log, task_log_path

        p = task_log_path("task-1")
        p.write_text("x\n", encoding="utf-8")
        cleanup_task_log("task-1")
        assert not p.exists()
        cleanup_task_log("task-1")  # 幂等不抛
