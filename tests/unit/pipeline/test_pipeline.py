"""Unit tests for Pipeline creation and initialization."""

import pytest

from mediafactory import Pipeline
from mediafactory.engine import AudioEngine, RecognitionEngine, TranslationEngine, SRTEngine

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
        assert len(pipeline.stages) == 6  # Model, Audio, Transcription, Translation, SRT, Cleanup

    def test_pipeline_create_audio_only(self):
        """Test audio-only pipeline creation."""
        audio_engine = AudioEngine()
        pipeline = Pipeline.create_audio_only(audio_engine)
        assert pipeline is not None
        assert len(pipeline.stages) == 1
