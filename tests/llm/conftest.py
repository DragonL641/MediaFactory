"""LLM 后端测试的统一 fixtures 和辅助类（使用 Mock）。

注意：此目录下的测试使用 Mock，不进行真实 API 调用。
对于真实 API 调测，请使用 scripts/debug/ 目录下的脚本。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from mediafactory.llm.base import TranslationRequest, TranslationResult
from mediafactory.llm import OpenAICompatibleBackend


class LLMBackendTestMixin:
    """LLM 后端测试的混合基类（使用 Mock）。

    提供统一的测试模式，子类只需指定后端名称。
    所有 API 调用都被 Mock，不进行真实网络请求。
    """

    # 子类需要覆盖的属性
    backend_name: str = "openai_compatible"  # 后端名称
    default_model: str = "gpt-4o-mini"  # 默认模型名称

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """测试前设置。"""
        print(f"\n[测试] {self.backend_display_name} 后端测试 (Mock)")

    @property
    def backend_display_name(self) -> str:
        """获取后端显示名称。"""
        return self.backend_name.upper()

    def _create_mock_backend(self):
        """创建 Mock 后端实例。"""
        backend = Mock()
        backend.name = self.backend_name
        backend.model = self.default_model
        backend.is_available = True

        # Mock translate 方法
        def mock_translate(request):
            # 简单的 Mock 翻译逻辑
            if isinstance(request.text, list):
                translated = [f"[{self.backend_name}] {t}" for t in request.text]
            else:
                translated = [f"[{self.backend_name}] {request.text}"]
            return TranslationResult(
                success=True,
                translated_text=translated,
                backend_used=self.backend_name,
            )

        backend.translate = mock_translate

        # Mock test_connection 方法
        backend.test_connection.return_value = {
            "success": True,
            "message": "Connection successful",
        }

        return backend

    # ========== 核心测试方法（使用 Mock） ==========

    @pytest.mark.unit
    def test_backend_creation(self):
        """测试后端创建。"""
        backend = OpenAICompatibleBackend(
            api_key="test_key",
            base_url="https://api.test.com/v1",
            model=self.default_model,
        )
        assert backend is not None
        assert backend.name == self.backend_name
        print(f"✅ {self.backend_display_name} 后端创建测试通过!")

    @pytest.mark.unit
    def test_translate_single_text(self):
        """测试单句翻译（Mock）。"""
        backend = self._create_mock_backend()

        request = TranslationRequest(
            text="Hello, world!",
            src_lang="en",
            tgt_lang="zh",
        )
        result = backend.translate(request)

        assert result.success
        assert len(result.translated_text) == 1
        assert self.backend_name in result.translated_text[0]
        print(f"✅ {self.backend_display_name} 单句翻译测试通过!")

    @pytest.mark.unit
    def test_translate_batch_text(self):
        """测试批量翻译（Mock）。"""
        backend = self._create_mock_backend()

        texts = ["Hello", "World", "Test"]
        request = TranslationRequest(text=texts, src_lang="en", tgt_lang="zh")
        result = backend.translate(request)

        assert result.success
        assert len(result.translated_text) == len(texts)
        print(f"✅ {self.backend_display_name} 批量翻译测试通过!")

    @pytest.mark.unit
    def test_translate_with_context(self):
        """测试带上下文的翻译（Mock）。"""
        backend = self._create_mock_backend()

        request = TranslationRequest(
            text="Hello",
            src_lang="en",
            tgt_lang="zh",
            prev_text="Hi there",
            next_text="Goodbye",
        )
        result = backend.translate(request)

        assert result.success
        print(f"✅ {self.backend_display_name} 上下文翻译测试通过!")

    @pytest.mark.unit
    def test_connection_test(self):
        """测试连接测试方法（Mock）。"""
        backend = self._create_mock_backend()

        result = backend.test_connection()
        assert result["success"]
        print(f"✅ {self.backend_display_name} 连接测试通过!")

    @pytest.mark.unit
    def test_backend_properties(self):
        """测试后端属性。"""
        backend = OpenAICompatibleBackend(
            api_key="test_key",
            base_url="https://api.test.com/v1",
            model=self.default_model,
        )

        assert hasattr(backend, "name")
        assert hasattr(backend, "is_available")
        assert backend.name == self.backend_name

        print(f"✅ {self.backend_display_name} 属性测试通过!")


class LLMBackendErrorTestMixin:
    """LLM 后端错误处理测试的混合基类。"""

    backend_name: str = "openai_compatible"
    default_model: str = "gpt-4o-mini"

    @pytest.mark.unit
    def test_translate_with_error(self):
        """测试翻译错误处理（Mock）。"""
        backend = Mock()
        backend.name = self.backend_name
        backend.translate.return_value = TranslationResult(
            success=False,
            translated_text=[],
            error_message="API Error: Rate limit exceeded",
            backend_used=self.backend_name,
        )

        request = TranslationRequest(
            text="Hello",
            src_lang="en",
            tgt_lang="zh",
        )
        result = backend.translate(request)

        assert not result.success
        assert "Error" in result.error_message

    @pytest.mark.unit
    def test_empty_api_key(self):
        """测试空 API Key 的错误处理（Mock）。"""
        backend = Mock()
        backend.is_available = False
        backend.test_connection.return_value = {
            "success": False,
            "message": "API key is empty",
        }

        result = backend.test_connection()
        assert not result["success"]
        assert "empty" in result["message"].lower()

    @pytest.mark.unit
    def test_invalid_api_key(self):
        """测试无效 API Key 的错误处理（Mock）。"""
        backend = Mock()
        backend.is_available = False
        backend.test_connection.return_value = {
            "success": False,
            "message": "Invalid API key",
        }

        result = backend.test_connection()
        assert not result["success"]


# ========== 共享 Mock Fixtures ==========


@pytest.fixture
def mock_translation_response():
    """提供 Mock 翻译响应。"""
    return TranslationResult(
        success=True,
        translated_text=["测试译文"],
        backend_used="mock",
    )


@pytest.fixture
def mock_backend():
    """提供 Mock 后端实例。"""
    backend = Mock()
    backend.name = "mock"
    backend.is_available = True
    backend.translate.return_value = TranslationResult(
        success=True,
        translated_text=["测试译文"],
        backend_used="mock",
    )
    return backend


@pytest.fixture
def mock_openai_client():
    """提供 Mock OpenAI 兼容客户端。"""
    client = Mock()
    response = Mock()
    response.choices = [Mock(message=Mock(content="测试译文"))]
    client.chat.completions.create.return_value = response
    return client


@pytest.fixture(scope="session")
def sample_translation_texts():
    """提供标准测试文本。"""
    return {
        "simple": "Hello, world!",
        "batch": [
            "Hello, how are you?",
            "This is a test of translation system.",
            "AI is transforming the world.",
        ],
        "subtitle": [
            "おはようございます。",
            "今日はいい天気ですね。",
            "一緒に買い物に行きませんか？",
        ],
        "empty": "",
        "long": "This is a very long text that might need special handling in translation systems. "
        * 10,
    }
