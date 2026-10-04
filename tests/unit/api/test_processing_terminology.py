"""翻译/字幕任务创建 API 的 terminology 透传集成测试。

评审 Critical 1 回归防线：Request 模型与路由组装必须把 terminology
送达 TaskConfig，否则整个术语功能经 API 不可达（前端值被静默丢弃）。
"""

import pytest
from fastapi.testclient import TestClient

from mediafactory.api.schemas import TaskConfig, TaskType

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


class TestTerminologyPassthrough:
    def test_translate_request_accepts_terminology(self):
        """TranslateRequest 模型必须有 terminology 字段。"""
        from mediafactory.api.schemas import TranslateRequest

        req = TranslateRequest(text="hello", terminology={"Kubernetes": "K8s"})
        assert req.terminology == {"Kubernetes": "K8s"}

    def test_subtitle_request_accepts_terminology(self):
        """SubtitleRequest 模型必须有 terminology 字段。"""
        from mediafactory.api.schemas import SubtitleRequest

        req = SubtitleRequest(video_path="v.mp4", terminology={"Kubernetes": "K8s"})
        assert req.terminology == {"Kubernetes": "K8s"}

    def test_post_translate_delivers_terminology_to_task_config(
        self, client_with_captured_config
    ):
        client, captured = client_with_captured_config
        resp = client.post(
            "/api/processing/translate",
            json={
                "text": "Hello Kubernetes",
                "source_lang": "en",
                "target_lang": "zh",
                "use_llm": True,
                "terminology": {"Kubernetes": "K8s"},
            },
        )
        assert resp.status_code == 200, resp.text
        config: TaskConfig = captured["config"]
        assert config.task_type == TaskType.TRANSLATE
        assert config.terminology == {"Kubernetes": "K8s"}

    def test_post_subtitle_delivers_terminology_to_task_config(
        self, client_with_captured_config
    ):
        client, captured = client_with_captured_config
        resp = client.post(
            "/api/processing/subtitle",
            json={
                "video_path": "v.mp4",
                "target_lang": "zh",
                "terminology": {"Kubernetes": "K8s"},
            },
        )
        assert resp.status_code == 200, resp.text
        config: TaskConfig = captured["config"]
        assert config.terminology == {"Kubernetes": "K8s"}

    def test_post_translate_over_200_entries_rejected(
        self, client_with_captured_config
    ):
        """评审 Review Focus 2：超限术语表经 API 必须 422，而不是静默创建。"""
        client, _ = client_with_captured_config
        big = {f"term{i}": f"词{i}" for i in range(201)}
        resp = client.post(
            "/api/processing/translate",
            json={"text": "hello", "terminology": big},
        )
        assert resp.status_code == 422
