"""创建任务 API 的 use_llm 缺省回归测试。

背景：UI 移除 use_llm 开关后，表单 payload 不再携带该字段（antd
validateFields 只返回已注册字段）。若 Request 默认 False，则 UI 创建的
字幕/翻译任务一律存成 use_llm=false，被单方向门拒绝——任务必失败。
契约：Request 缺省=LLM-only（True）；显式 false 仍被门拒绝。
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


class TestUseLlmDefault:
    def test_subtitle_request_without_use_llm_defaults_true(
        self, client_with_captured_config
    ):
        client, captured = client_with_captured_config
        resp = client.post(
            "/api/processing/subtitle",
            json={"video_path": "/tmp/v.mp4"},
        )
        assert resp.status_code == 200
        assert captured["config"].use_llm is True

    def test_translate_request_without_use_llm_defaults_true(
        self, client_with_captured_config
    ):
        client, captured = client_with_captured_config
        resp = client.post(
            "/api/processing/translate",
            json={"text": "hello", "target_lang": "ja"},
        )
        assert resp.status_code == 200
        assert captured["config"].use_llm is True
