"""本地模型路由 + pull 任务测试（Ollama client 全 mock）。"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from mediafactory.api.main import get_app


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
