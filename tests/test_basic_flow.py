"""Unit tests for MediaFactory basic flow."""

import pytest
from unittest.mock import MagicMock, patch

from mediafactory import Pipeline, ProcessingContext
from mediafactory.engine import AudioEngine, RecognitionEngine, TranslationEngine, SRTEngine


class TestBasicFlow:
    """Test basic pipeline flow coordination."""

    def test_pipeline_initialization(self):
        """Test Pipeline can be initialized."""
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

    def test_processing_context_creation(self):
        """Test ProcessingContext can be created."""
        ctx = ProcessingContext(
            video_path="/test/video.mp4",
            tgt_lang="zh",
        )
        assert ctx.video_path == "/test/video.mp4"
        assert ctx.tgt_lang == "zh"

    def test_processing_context_defaults(self):
        """Test ProcessingContext default values."""
        ctx = ProcessingContext()
        assert ctx.tgt_lang == "zh"
        assert ctx.whisper_model == "small"
