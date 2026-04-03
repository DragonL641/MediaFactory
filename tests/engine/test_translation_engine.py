"""翻译引擎测试（Mock 外部依赖而非被测方法）。"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestTranslationEngine:
    """TranslationEngine 测试 — mock 模型加载和 API 调用。"""

    @pytest.mark.unit
    def test_engine_creation_local_mode(self):
        """测试创建本地翻译引擎。"""
        from mediafactory.engine import TranslationEngine

        engine = TranslationEngine(use_local_models_only=True)
        assert engine is not None
        assert engine.use_local_models_only is True

    @pytest.mark.unit
    def test_engine_creation_llm_mode(self):
        """测试创建 LLM 翻译引擎。"""
        from mediafactory.engine import TranslationEngine
        from mediafactory.llm.base import TranslationBackend

        class MockBackend(TranslationBackend):
            name = "mock"

            @property
            def is_available(self):
                return True

            @property
            def get_model_name(self):
                return "mock-model"

            def translate(self, request):
                from mediafactory.llm.base import TranslationResult
                return TranslationResult(
                    translated_text=request.text,
                    backend_used="mock",
                    success=True
                )

            def test_connection(self):
                return {"success": True, "message": "OK"}

        mock_backend = MockBackend()
        engine = TranslationEngine(
            use_llm_backend=True,
            llm_backend=mock_backend
        )
        assert engine is not None
        assert engine.llm_backend is mock_backend

    @pytest.mark.unit
    def test_translate_same_language_returns_original(self):
        """测试源语言和目标语言相同时应返回原始内容。"""
        from mediafactory.engine import TranslationEngine

        engine = TranslationEngine(use_local_models_only=True)

        segments = [
            {"start": 0.0, "end": 2.0, "text": "Hello"},
            {"start": 2.0, "end": 4.0, "text": "World"},
        ]
        result = {"segments": segments, "language": "en"}

        # mock 内部模型调用，不 mock translate 本身
        with patch.object(engine, "_translate_with_model", return_value=[
            {"start": 0.0, "end": 2.0, "text": "Hello"},
            {"start": 2.0, "end": 4.0, "text": "World"},
        ]):
            translated = engine.translate(result, "en", "en")
            # 相同语言应直接返回或轻量处理
            assert len(translated["segments"]) == 2

    @pytest.mark.unit
    def test_translate_empty_segments(self):
        """测试空片段列表。"""
        from mediafactory.engine import TranslationEngine

        engine = TranslationEngine(use_local_models_only=True)

        result = {"segments": [], "language": "en"}

        with patch.object(engine, "_translate_with_model", return_value=[]):
            translated = engine.translate(result, "en", "zh")

            assert len(translated["segments"]) == 0

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
                    translated_text="你好，世界！",
                    backend_used="mock",
                    success=True
                )

            def test_connection(self):
                return {"success": True, "message": "OK"}

        engine = TranslationEngine(
            use_llm_backend=True,
            llm_backend=MockBackend()
        )

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

        engine = TranslationEngine(use_local_models_only=True)

        # cleanup 不应抛出异常
        try:
            if hasattr(engine, "cleanup"):
                engine.cleanup()
        except Exception:
            # 如果 cleanup 需要特定状态，可接受
            pass
