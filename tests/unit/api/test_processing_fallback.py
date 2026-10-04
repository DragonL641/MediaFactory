"""翻译/字幕任务创建 API 的 fallback_model 透传测试。

与 test_processing_terminology 同模式：Request 模型与路由组装必须把
fallback_model 送达 TaskConfig，否则任务级兜底经 API 不可达。
"""

import pytest
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.unit]


@pytest.fixture
def client_with_captured_config(monkeypatch):
    """TestClient + 捕获 create_task 收到的 TaskConfig。"""
    captured: dict = {}

    class FakeTaskManager:
        async def create_task(self, config, name=""):
            captured["config"] = config
            return "task-1"

    from mediafactory.api.routes import processing as processing_routes

    monkeypatch.setattr(
        processing_routes, "_get_task_manager", lambda: FakeTaskManager()
    )

    from mediafactory.api.main import get_app

    with TestClient(get_app()) as c:
        yield c, captured


class TestFallbackModelPassthrough:
    def test_translate_task_passes_fallback_model(self, client_with_captured_config):
        client, captured = client_with_captured_config
        resp = client.post(
            "/api/processing/translate",
            json={
                "text": "hello",
                "target_lang": "zh",
                "use_llm": True,
                "fallback_model": "qwen2.5:7b",
            },
        )
        assert resp.status_code == 200
        assert captured["config"].fallback_model == "qwen2.5:7b"

    def test_subtitle_task_passes_fallback_model(self, client_with_captured_config):
        client, captured = client_with_captured_config
        resp = client.post(
            "/api/processing/subtitle",
            json={
                "video_path": "/tmp/v.mp4",
                "use_llm": True,
                "fallback_model": "qwen2.5:7b",
            },
        )
        assert resp.status_code == 200
        assert captured["config"].fallback_model == "qwen2.5:7b"

    def test_translate_task_without_fallback_defaults_none(
        self, client_with_captured_config
    ):
        client, captured = client_with_captured_config
        resp = client.post(
            "/api/processing/translate",
            json={"text": "hello", "target_lang": "zh", "use_llm": True},
        )
        assert resp.status_code == 200
        assert captured["config"].fallback_model is None
