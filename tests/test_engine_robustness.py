import pytest
from mediafactory.engine.translation import TranslationEngine
from mediafactory.engine.srt import SRTEngine


class MockLLMBackend:
    """Mock LLM backend for testing."""

    name = "mock"

    @property
    def is_available(self):
        return True

    @property
    def get_model_name(self):
        return "mock-model"

    def translate(self, request):
        from mediafactory.llm.base import TranslationResult
        # Return empty translations for empty input
        if isinstance(request.text, list):
            return TranslationResult(
                translated_text=[""] * len(request.text),
                backend_used="mock",
                success=True
            )
        return TranslationResult(
            translated_text="",
            backend_used="mock",
            success=True
        )

    def test_connection(self):
        return {"success": True, "message": "OK"}


class TestEngineRobustness:
    """测试各引擎在边界情况下的鲁棒性。"""

    def test_translation_engine_empty_segments(self):
        """测试翻译引擎处理空分段的情况。"""
        # 使用 Mock LLM 后端测试，避免依赖本地模型
        mock_backend = MockLLMBackend()
        engine = TranslationEngine(
            use_llm_backend=True,
            llm_backend=mock_backend
        )
        result = {
            "segments": [
                {"text": "  ", "start": 0.0, "end": 1.0},
                {"text": "", "start": 1.0, "end": 2.0}
            ],
            "language": "en"
        }
        # 即使模型不可用，也应该能处理空文本而不会崩溃
        translated = engine.translate(result, src_lang="en", tgt_lang="zh")
        assert len(translated["segments"]) == 2
        assert translated["segments"][0]["text"].strip() == ""
        assert translated["segments"][1]["text"].strip() == ""

    def test_srt_timestamp_formatting(self):
        """测试 SRT 时间戳格式化。"""
        engine = SRTEngine()
        assert engine._format_timestamp(0) == "00:00:00,000"
        assert engine._format_timestamp(3661.5) == "01:01:01,500"
        assert engine._format_timestamp(59.999) == "00:00:59,999"
