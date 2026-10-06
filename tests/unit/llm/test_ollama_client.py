"""OllamaClient 单元测试（httpx.MockTransport，无网络）。"""

import asyncio
import json

import httpx
import pytest

from mediafactory.llm.ollama_client import OllamaClient, OllamaError

pytestmark = pytest.mark.unit

TAGS_BODY = {
    "models": [
        {
            "name": "qwen2.5:7b",
            "size": 4683087332,
            "modified_at": "2026-03-04T00:07:38Z",
            "details": {"parameter_size": "7.6B", "quantization_level": "Q4_K_M"},
        }
    ]
}
PS_LOADED = {"models": [{"name": "qwen2.5:7b"}]}
PS_EMPTY = {"models": []}


def _make(handler) -> OllamaClient:
    return OllamaClient(transport=httpx.MockTransport(handler))


def test_is_available_true():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tags"
        return httpx.Response(200, json=TAGS_BODY)

    assert asyncio.run(_make(handler).is_available()) is True


def test_is_available_false_when_down():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    assert asyncio.run(_make(handler).is_available()) is False


def test_list_installed_parses_details():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=TAGS_BODY)

    models = asyncio.run(_make(handler).list_installed())
    assert models[0].name == "qwen2.5:7b"
    assert models[0].parameter_size == "7.6B"
    assert models[0].quantization_level == "Q4_K_M"


def test_pull_stream_yields_events_and_raises_on_error_line():
    body = (
        json.dumps({"status": "pulling manifest"}).encode()
        + b"\n"
        + json.dumps({"status": "pulling x", "total": 100, "completed": 50}).encode()
        + b"\n"
        + json.dumps({"status": "success"}).encode()
        + b"\n"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/pull"
        assert json.loads(request.content)["name"] == "qwen2.5:7b"
        return httpx.Response(200, content=body)

    async def consume():
        return [e async for e in _make(handler).pull_stream("qwen2.5:7b")]

    events = asyncio.run(consume())
    assert events[0]["status"] == "pulling manifest"
    assert events[1]["completed"] == 50
    assert events[-1]["status"] == "success"


def test_pull_stream_raises_ollama_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b'{"error": "model not found"}\n')

    async def consume():
        async for _ in _make(handler).pull_stream("nope"):
            pass

    with pytest.raises(OllamaError):
        asyncio.run(consume())


def test_unload_model_sync_skips_when_not_loaded():
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.path == "/api/ps":
            return httpx.Response(200, json=PS_EMPTY)
        return httpx.Response(200, json={})

    _make(handler).unload_model_sync("qwen2.5:7b")
    # 未加载 → 不得触发 generate（否则 Ollama 会先加载再卸载，白占内存）
    assert all(r.url.path != "/api/generate" for r in calls)


def test_unload_model_sync_unloads_loaded_model():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/ps":
            return httpx.Response(200, json=PS_LOADED)
        assert json.loads(request.content) == {
            "model": "qwen2.5:7b",
            "keep_alive": 0,
        }
        return httpx.Response(200, json={"done": True, "done_reason": "unload"})

    _make(handler).unload_model_sync("qwen2.5:7b")


def test_unload_model_sync_swallows_connection_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    _make(handler).unload_model_sync("qwen2.5:7b")  # 不抛异常即通过


def test_is_model_installed_sync():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=TAGS_BODY)

    client = _make(handler)
    assert client.is_model_installed_sync("qwen2.5:7b") is True
    assert client.is_model_installed_sync("nope:1b") is False


def test_delete_model():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        assert json.loads(request.content) == {"name": "qwen2.5:7b"}
        return httpx.Response(200)

    asyncio.run(_make(handler).delete_model("qwen2.5:7b"))
