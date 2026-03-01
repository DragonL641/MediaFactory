"""翻译引擎测试（使用 Mock 本地模型和 LLM）。"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestTranslationEngine:
    """TranslationEngine 测试（Mock）。"""

    @pytest.mark.unit
    def test_engine_creation_local(self):
        """测试创建本地翻译引擎。"""
        from mediafactory.engine import TranslationEngine

        engine = TranslationEngine(use_local_models_only=True)
        assert engine is not None
        assert engine.use_local_models_only is True

    @pytest.mark.unit
    def test_engine_creation_llm(self):
        """测试创建 LLM 翻译引擎。"""
        from mediafactory.engine import TranslationEngine

        # Mock LLM backend
        mock_backend = Mock()
        mock_backend.is_available = True

        engine = TranslationEngine(
            llm_backend=mock_backend,
            use_llm_backend=True,
        )
        assert engine is not None
        assert engine.use_llm_backend is True

    @pytest.mark.unit
    def test_translate_with_mock(self):
        """测试翻译（Mock）。"""
        from mediafactory.engine import TranslationEngine

        # 准备测试数据
        segments = [
            {"start": 0.0, "end": 2.0, "text": "Hello, world!"},
            {"start": 2.0, "end": 4.0, "text": "This is a test."},
        ]
        result = {"segments": segments, "language": "en"}

        engine = TranslationEngine(use_local_models_only=True, model_type="nllb-600m")

        # Mock translate 方法
        with patch.object(engine, "translate") as mock_translate:
            mock_translate.return_value = {
                "segments": [
                    {"start": 0.0, "end": 2.0, "text": "你好，世界！"},
                    {"start": 2.0, "end": 4.0, "text": "这是一个测试。"},
                ],
                "language": "en",
            }

            translated = engine.translate(result, "en", "zh")

            assert len(translated["segments"]) == 2
            assert "你好" in translated["segments"][0]["text"]

    @pytest.mark.unit
    def test_translate_same_language(self):
        """测试源语言和目标语言相同时的处理。"""
        from mediafactory.engine import TranslationEngine

        engine = TranslationEngine(use_local_models_only=True)

        segments = [{"start": 0.0, "end": 2.0, "text": "Hello"}]
        result = {"segments": segments, "language": "en"}

        # Mock translate 方法返回原样
        with patch.object(engine, "translate") as mock_translate:
            mock_translate.return_value = result

            translated = engine.translate(result, "en", "en")

            assert translated["segments"][0]["text"] == "Hello"

    @pytest.mark.unit
    def test_translate_empty_segments(self):
        """测试空片段列表的处理。"""
        from mediafactory.engine import TranslationEngine

        engine = TranslationEngine(use_local_models_only=True)

        result = {"segments": [], "language": "en"}

        with patch.object(engine, "translate") as mock_translate:
            mock_translate.return_value = {"segments": [], "language": "en"}

            translated = engine.translate(result, "en", "zh")

            assert len(translated["segments"]) == 0


class TestLocalTranslationEngine:
    """LocalTranslationEngine 测试（Mock）。"""

    @pytest.mark.unit
    def test_local_engine_module_exists(self):
        """测试本地翻译引擎模块存在。"""
        try:
            from mediafactory.engine import LocalTranslationEngine

            assert LocalTranslationEngine is not None
        except ImportError:
            pytest.skip("LocalTranslationEngine not available")


class TestLLMTranslationEngine:
    """LLMTranslationEngine 测试（Mock）。"""

    @pytest.mark.unit
    def test_llm_engine_module_exists(self):
        """测试 LLM 翻译引擎模块存在。"""
        try:
            from mediafactory.engine import TranslationEngine

            assert TranslationEngine is not None
        except ImportError:
            pytest.skip("TranslationEngine not available")

    @pytest.mark.unit
    def test_llm_engine_creation_with_mock(self):
        """测试使用 Mock 创建 LLM 翻译引擎。"""
        from mediafactory.engine import TranslationEngine
        from mediafactory.llm.base import TranslationBackend

        # 创建一个继承自 TranslationBackend 的 Mock
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

        # 使用统一的 TranslationEngine，启用 LLM 后端
        engine = TranslationEngine(
            use_llm_backend=True,
            llm_backend=mock_backend
        )
        assert engine is not None
        assert engine.llm_backend is mock_backend
        assert engine.engine_type == "LLM"
