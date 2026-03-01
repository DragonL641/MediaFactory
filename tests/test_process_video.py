"""Unit tests for the MediaFactory engine module."""

from mediafactory import Pipeline, ProcessingContext
from mediafactory.engine import AudioEngine, RecognitionEngine, TranslationEngine, SRTEngine


class TestPipelineCreation:
    """Test suite for Pipeline creation."""

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


class TestSRTEngine:
    """Test suite for SRTEngine class."""

    def test_format_timestamp_method(self):
        """Test the timestamp formatting method."""
        engine = SRTEngine()
        # Test basic formatting
        assert engine._format_timestamp(0) == "00:00:00,000"
        assert engine._format_timestamp(1) == "00:00:01,000"
        assert engine._format_timestamp(60) == "00:01:00,000"
        assert engine._format_timestamp(3600) == "01:00:00,000"

        # Test with fractional seconds
        assert engine._format_timestamp(1.5) == "00:00:01,500"
        assert engine._format_timestamp(61.25) == "00:01:01,250"
