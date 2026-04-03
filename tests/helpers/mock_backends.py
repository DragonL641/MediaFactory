"""共享 Mock 后端，替代各测试文件中的重复定义。"""

from unittest.mock import Mock
from mediafactory.llm.base import TranslationBackend, TranslationResult


class MockLLMBackend(TranslationBackend):
    """用于测试的 Mock LLM 后端。"""

    name = "mock"

    @property
    def is_available(self):
        return True

    @property
    def get_model_name(self):
        return "mock-model"

    def translate(self, request):
        if isinstance(request.text, list):
            return TranslationResult(
                translated_text=[""] * len(request.text),
                backend_used="mock",
                success=True,
            )
        return TranslationResult(
            translated_text="",
            backend_used="mock",
            success=True,
        )

    def test_connection(self):
        return {"success": True, "message": "OK"}


def create_mock_backend(**overrides):
    """创建 Mock 后端实例，支持自定义行为。"""
    backend = Mock()
    backend.name = overrides.get("name", "mock")
    backend.is_available = overrides.get("is_available", True)
    backend.get_model_name = overrides.get("get_model_name", "mock-model")
    backend.test_connection.return_value = {"success": True, "message": "OK"}
    return backend
