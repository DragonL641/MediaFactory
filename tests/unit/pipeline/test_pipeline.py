"""Unit tests for Pipeline creation and initialization."""

import pytest

from mediafactory import Pipeline
from mediafactory.engine import (
    AudioEngine,
    RecognitionEngine,
    SRTEngine,
    TranslationEngine,
)

pytestmark = [pytest.mark.unit]


class TestPipeline:
    """Tests for Pipeline creation methods."""

    def test_pipeline_initialization(self):
        """Test Pipeline can be initialized with default stages."""
        audio_engine = AudioEngine()
        recognition_engine = RecognitionEngine()
        translation_engine = TranslationEngine()
        srt_engine = SRTEngine()

        pipeline = Pipeline.create_default(
            audio_engine=audio_engine,
            recognition_engine=recognition_engine,
            translation_engine=translation_engine,
            srt_engine=srt_engine,
        )
        assert pipeline is not None
        assert len(pipeline.stages) > 0

    def test_pipeline_create_default(self):
        """Test default pipeline creation."""
        audio_engine = AudioEngine()
        recognition_engine = RecognitionEngine()
        translation_engine = TranslationEngine()
        srt_engine = SRTEngine()

        pipeline = Pipeline.create_default(
            audio_engine=audio_engine,
            recognition_engine=recognition_engine,
            translation_engine=translation_engine,
            srt_engine=srt_engine,
        )
        assert pipeline is not None
        # Model, Audio, Transcription, PostProcess, Translation, SRT
        assert len(pipeline.stages) == 6


# ============================================================================
# R3: translation_stats 进 ProcessingResult.metadata
# ============================================================================


class TestTranslationStatsMetadata:
    def test_translation_stats_flow_to_metadata(self):
        """TranslationStage 写入的 translation_stats 进入 ProcessingResult.metadata。"""
        from mediafactory.pipeline.context import ProcessingContext
        from mediafactory.pipeline.pipeline import Pipeline
        from mediafactory.pipeline.stages import TranslationStage

        class _FakeEngine:
            def translate(self, result, src, tgt, progress, detection_context=""):
                out = result.copy()
                out["translation_stats"] = {
                    "total": 1,
                    "remote": 1,
                    "fallback": 0,
                    "failed": 0,
                }
                return out

        context = ProcessingContext(src_lang="en", tgt_lang="zh")
        context.transcription_result = {"segments": [{"text": "hi"}]}

        result = Pipeline([TranslationStage(_FakeEngine())]).execute(context)

        assert result.success is True
        assert result.metadata == {
            "translation_stats": {"total": 1, "remote": 1, "fallback": 0, "failed": 0}
        }
