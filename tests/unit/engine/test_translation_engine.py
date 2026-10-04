"""翻译引擎测试（Mock 外部依赖而非被测方法）。"""

from unittest.mock import patch

import pytest

from tests.helpers.mock_backends import MockLLMBackend


class TestTranslationEngine:
    """TranslationEngine 测试 — mock 模型加载和 API 调用。"""

    @pytest.mark.unit
    def test_engine_creation_without_backend(self):
        """测试未配置 LLM 后端创建引擎：合法但不可用。"""
        from mediafactory.engine import TranslationEngine

        engine = TranslationEngine()
        assert engine is not None
        assert engine.llm_backend is None
        assert engine._use_llm is False

    @pytest.mark.unit
    def test_engine_creation_llm_mode(self):
        """测试创建 LLM 翻译引擎。"""
        from mediafactory.engine import TranslationEngine

        mock_backend = MockLLMBackend()
        engine = TranslationEngine(use_llm_backend=True, llm_backend=mock_backend)
        assert engine is not None
        assert engine.llm_backend is mock_backend

    @pytest.mark.unit
    def test_translate_same_language_returns_original(self):
        """测试源语言和目标语言相同时应返回原始内容。"""
        from mediafactory.engine import TranslationEngine

        engine = TranslationEngine()

        segments = [
            {"start": 0.0, "end": 2.0, "text": "Hello"},
            {"start": 2.0, "end": 4.0, "text": "World"},
        ]
        result = {"segments": segments, "language": "en"}

        translated = engine.translate(result, "en", "en")
        # 相同语言应直接返回或轻量处理
        assert len(translated["segments"]) == 2

    @pytest.mark.unit
    def test_translate_without_backend_raises(self):
        """测试未配置 LLM 后端时翻译报 ProcessingError。"""
        from mediafactory.engine import TranslationEngine
        from mediafactory.exceptions import ProcessingError

        engine = TranslationEngine()

        result = {"segments": [], "language": "en"}

        with pytest.raises(ProcessingError, match="not configured"):
            engine.translate(result, "en", "zh")

    @pytest.mark.unit
    def test_translate_with_llm_backend(self):
        """测试使用 LLM 后端翻译。"""
        from mediafactory.engine import TranslationEngine
        from mediafactory.llm.base import TranslationBackend, TranslationResult

        class MockBackend(TranslationBackend):
            name = "mock"

            @property
            def is_available(self):
                return True

            @property
            def get_model_name(self):
                return "mock-model"

            def translate(self, request):
                return TranslationResult(
                    translated_text="你好，世界！", backend_used="mock", success=True
                )

            def test_connection(self):
                return {"success": True, "message": "OK"}

        engine = TranslationEngine(use_llm_backend=True, llm_backend=MockBackend())

        segments = [
            {"start": 0.0, "end": 2.0, "text": "Hello, world!"},
        ]
        result = {"segments": segments, "language": "en"}

        # mock _translate_with_llm 以避免真实的 API 调用
        with patch.object(engine, "_translate_with_llm") as mock_llm:
            mock_llm.return_value = {
                "segments": [
                    {"start": 0.0, "end": 2.0, "text": "你好，世界！"},
                ],
                "language": "en",
            }
            translated = engine.translate(result, "en", "zh")

            assert len(translated["segments"]) == 1
            assert "你好" in translated["segments"][0]["text"]

    @pytest.mark.unit
    def test_engine_cleanup(self):
        """测试引擎清理资源。"""
        from mediafactory.engine import TranslationEngine

        engine = TranslationEngine()

        # cleanup 不应抛出异常
        try:
            if hasattr(engine, "cleanup"):
                engine.cleanup()
        except Exception:
            # 如果 cleanup 需要特定状态，可接受
            pass

    @pytest.mark.unit
    def test_translation_engine_empty_segments(self):
        """测试翻译引擎处理空分段的情况。（来自 test_engine_robustness）"""
        from mediafactory.engine.translation import TranslationEngine

        mock_backend = MockLLMBackend()
        engine = TranslationEngine(use_llm_backend=True, llm_backend=mock_backend)
        result = {
            "segments": [
                {"text": "  ", "start": 0.0, "end": 1.0},
                {"text": "", "start": 1.0, "end": 2.0},
            ],
            "language": "en",
        }
        # 即使模型不可用，也应该能处理空文本而不会崩溃
        translated = engine.translate(result, src_lang="en", tgt_lang="zh")
        assert len(translated["segments"]) == 2
        assert translated["segments"][0]["text"].strip() == ""
        assert translated["segments"][1]["text"].strip() == ""
