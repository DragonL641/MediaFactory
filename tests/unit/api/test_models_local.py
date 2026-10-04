"""本地模型路由 + pull 任务测试（Ollama client 全 mock）。"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from mediafactory.api.main import get_app
from mediafactory.api.schemas import TaskStatus


@pytest.fixture
def client():
    return TestClient(get_app())


def _patch_client(available=True, models=None, monkeypatch=None):
    fake = MagicMock()
    fake.is_available = AsyncMock(return_value=available)
    fake.list_installed = AsyncMock(return_value=models or [])
    fake.delete_model = AsyncMock()
    fake.pull_stream = MagicMock()
    monkeypatch.setattr(
        "mediafactory.api.routes.local_models.get_ollama_client", lambda: fake
    )
    return fake


def test_local_models_unavailable(client, monkeypatch):
    _patch_client(available=False, monkeypatch=monkeypatch)
    resp = client.get("/api/models/local")
    assert resp.status_code == 200
    assert resp.json() == {"available": False, "models": []}


def test_local_models_lists_camel_case(client, monkeypatch):
    model = MagicMock(
        name="qwen2.5:7b",
        size=4683087332,
        parameter_size="7.6B",
        quantization_level="Q4_K_M",
        modified_at="2026-03-04T00:07:38Z",
    )
    _patch_client(models=[model], monkeypatch=monkeypatch)
    body = client.get("/api/models/local").json()
    assert body["available"] is True
    assert body["models"][0]["parameterSize"] == "7.6B"
    assert body["models"][0]["quantizationLevel"] == "Q4_K_M"


def test_pull_rejects_invalid_name(client, monkeypatch):
    _patch_client(monkeypatch=monkeypatch)
    resp = client.post("/api/models/local/pull", json={"name": "bad name!!"})
    assert resp.status_code == 422


def test_pull_returns_task_id(client, monkeypatch):
    # patch 掉 pull 协程的 Ollama client：空流 → 任务立即走 COMPLETED，不触网
    import mediafactory.api.local_pull_task as pull_task

    fake = MagicMock()

    async def _empty_stream(name):
        return
        yield  # pragma: no cover

    fake.pull_stream = _empty_stream
    monkeypatch.setattr(pull_task, "get_ollama_client", lambda: fake)

    resp = client.post("/api/models/local/pull", json={"name": "qwen2.5:0.5b"})
    assert resp.status_code == 200
    assert "task_id" in resp.json()


def test_pull_conflict_on_same_name(client, monkeypatch):
    _patch_client(monkeypatch=monkeypatch)
    import mediafactory.api.local_pull_task as pull_task

    monkeypatch.setattr(pull_task, "_active_pulls", {"qwen2.5:0.5b"})
    resp = client.post("/api/models/local/pull", json={"name": "qwen2.5:0.5b"})
    assert resp.status_code == 409


def test_delete_conflict_while_pulling(client, monkeypatch):
    _patch_client(monkeypatch=monkeypatch)
    import mediafactory.api.local_pull_task as pull_task

    monkeypatch.setattr(pull_task, "_active_pulls", {"qwen2.5:0.5b"})
    resp = client.delete("/api/models/local/qwen2.5:0.5b")
    assert resp.status_code == 409


def test_delete_unavailable_returns_503(client, monkeypatch):
    _patch_client(available=False, monkeypatch=monkeypatch)
    resp = client.delete("/api/models/local/qwen2.5:0.5b")
    assert resp.status_code == 503


def test_delete_success(client, monkeypatch):
    fake = _patch_client(monkeypatch=monkeypatch)
    resp = client.delete("/api/models/local/qwen2.5:0.5b")
    assert resp.status_code == 200
    fake.delete_model.assert_awaited_once_with("qwen2.5:0.5b")


# ============================================================================
# 评审修复：pull 任务终态保护（取消后协程不得覆写 CANCELLED）
# ============================================================================


def _run_cancel_overwrite_scenario(monkeypatch, stream_error: Exception):
    """构造：任务已被 cancel_task 置 CANCELLED，随后流异常/正常结束。"""
    import mediafactory.api.local_pull_task as pull_task

    captured: dict = {}

    class _FakeTaskManager:
        async def create_task(self, config, name=None):
            return "t-1"

        async def update_task_status(self, task_id, status, **kw):
            # 只捕获终态写入（RUNNING 是协程正常起点）
            if status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                captured["final"] = status

        async def get_task_status(self, task_id):
            return {"status": "cancelled"}

    class _FakeWS:
        async def broadcast_progress(self, **kw):
            pass

        async def broadcast_task_complete(self, **kw):
            pass

    monkeypatch.setattr(pull_task, "get_task_manager", lambda: _FakeTaskManager())
    monkeypatch.setattr(pull_task, "ws_manager", _FakeWS())

    fake = MagicMock()

    async def _stream(name):
        yield {"status": "pulling x", "total": 100, "completed": 1}
        raise stream_error

    fake.pull_stream = _stream
    monkeypatch.setattr(pull_task, "get_ollama_client", lambda: fake)

    asyncio.run(pull_task._execute_pull_task("t-1", "m:1", None))
    return captured


def test_pull_cancelled_then_stream_error_stays_cancelled(monkeypatch):
    """取消后流异常：终态必须保持 CANCELLED，不得覆写为 FAILED。"""

    captured = _run_cancel_overwrite_scenario(
        monkeypatch, RuntimeError("connection reset")
    )
    assert "final" not in captured  # 协程不得再写任何终态


def test_pull_cancelled_then_success_stays_cancelled(monkeypatch):
    """取消后流恰好正常结束：不得覆写为 COMPLETED。"""
    import mediafactory.api.local_pull_task as pull_task
    from mediafactory.api.schemas import TaskStatus

    captured: dict = {}

    class _FakeTaskManager:
        async def create_task(self, config, name=None):
            return "t-1"

        async def update_task_status(self, task_id, status, **kw):
            # 只捕获终态写入（RUNNING 是协程正常起点）
            if status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                captured["final"] = status

        async def get_task_status(self, task_id):
            return {"status": "cancelled"}

    class _FakeWS:
        async def broadcast_progress(self, **kw):
            pass

        async def broadcast_task_complete(self, **kw):
            pass

    monkeypatch.setattr(pull_task, "get_task_manager", lambda: _FakeTaskManager())
    monkeypatch.setattr(pull_task, "ws_manager", _FakeWS())

    fake = MagicMock()

    async def _stream(name):
        yield {"status": "success"}

    fake.pull_stream = _stream
    monkeypatch.setattr(pull_task, "get_ollama_client", lambda: fake)

    asyncio.run(pull_task._execute_pull_task("t-1", "m:1", None))
    assert "final" not in captured
