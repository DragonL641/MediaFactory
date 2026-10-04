"""OpenAICompatibleBackend 术语记忆集成测试（mock LLM client）。"""

import pytest

from mediafactory.llm import OpenAICompatibleBackend
from mediafactory.llm.base import TranslationRequest

pytestmark = [pytest.mark.unit]


class FakeResponse:
    def __init__(self, content: str):
        self.choices = [
            type("C", (), {"message": type("M", (), {"content": content})()})()
        ]


class FakeClient:
    """按顺序返回预设响应，并记录全部请求。"""

    def __init__(self, contents: list[str]):
        self._contents = list(contents)
        self.calls: list[dict] = []
        self.chat = type("Chat", (), {})()
        self.chat.completions = type("Completions", (), {})()
        self.chat.completions.create = self._create

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return FakeResponse(self._contents.pop(0) if self._contents else "{}")


def make_backend(contents: list[str]) -> tuple[OpenAICompatibleBackend, FakeClient]:
    backend = OpenAICompatibleBackend(
        api_key="test", base_url="https://api.test.com/v1", model="m", batch_size=40
    )
    client = FakeClient(contents)
    backend._client = client
    return backend, client


def _msg_content(call: dict) -> str:
    return "\n".join(m["content"] for m in call["messages"])


class TestInjection:
    def test_user_terms_injected_into_translation_prompt(self):
        backend, client = make_backend(['{"1": "你好 K8s 世界"}'])
        request = TranslationRequest(
            text=["Hello Kubernetes world"],
            src_lang="en",
            tgt_lang="zh",
            user_terms={"Kubernetes": "K8s"},
        )
        backend.translate(request)
        assert "# Terminology (must follow)" in _msg_content(client.calls[0])
        assert "- kubernetes → K8s" in _msg_content(client.calls[0])

    def test_no_terms_no_injection(self):
        backend, client = make_backend(['{"1": "你好"}'])
        request = TranslationRequest(text=["Hello"], src_lang="en", tgt_lang="zh")
        backend.translate(request)
        assert "# Terminology" not in _msg_content(client.calls[0])
