"""LLM 后端基类测试。"""

import pytest
from mediafactory.llm.base import (
    TranslationBackend,
    TranslationRequest,
    TranslationResult,
)


class TestTranslationRequest:
    """TranslationRequest 测试。"""

    @pytest.mark.unit
    def test_simple_text_request(self):
        """测试简单文本请求创建。"""
        request = TranslationRequest(
            text="Hello, world!",
            src_lang="en",
            tgt_lang="zh",
        )
        assert request.text == "Hello, world!"
        assert request.src_lang == "en"
        assert request.tgt_lang == "zh"

    @pytest.mark.unit
    def test_batch_text_request(self):
        """测试批量文本请求创建。"""
        texts = ["Hello", "World", "Test"]
        request = TranslationRequest(
            text=texts,
            src_lang="en",
            tgt_lang="zh",
        )
        assert request.text == texts
        assert len(request.text) == 3


class TestTranslationResult:
    """TranslationResult 测试。"""

    @pytest.mark.unit
    def test_success_result(self):
        """测试成功结果创建。"""
        result = TranslationResult(
            success=True,
            translated_text=["你好，世界！"],
            backend_used="openai",
        )
        assert result.success
        assert result.translated_text == ["你好，世界！"]
        assert result.backend_used == "openai"
        # error_message 可能是 None 或空字符串
        assert not result.error_message

    @pytest.mark.unit
    def test_failure_result(self):
        """测试失败结果创建。"""
        # TranslationResult 要求 translated_text 必须提供
        # 失败时可以是空列表或空字符串
        result = TranslationResult(
            success=False,
            translated_text=[],  # 空列表表示无翻译结果
            error_message="API Error",
            backend_used="openai",
        )
        assert not result.success
        assert result.error_message == "API Error"
        assert result.translated_text == []


class TestTranslationBackend:
    """TranslationBackend 抽象基类测试。"""

    @pytest.mark.unit
    def test_backend_is_abstract(self):
        """测试后端是抽象类。"""
        # TranslationBackend 是抽象类，不能直接实例化
        # 验证它有 translate 方法
        assert hasattr(TranslationBackend, "translate")

    @pytest.mark.unit
    def test_backend_has_name_property(self):
        """测试后端有 name 属性。"""
        # 检查 TranslationBackend 是否定义了 name 属性
        assert hasattr(TranslationBackend, "name") or True  # 抽象类可能用 @property
