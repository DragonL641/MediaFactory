"""Unit tests for ProcessingContext and ProcessingResult."""

import pytest

from mediafactory import ProcessingContext, ProcessingResult
from mediafactory.exceptions import (
    ConfigurationError,
    MediaFactoryError,
    ProcessingError,
)

pytestmark = [pytest.mark.unit]


class TestProcessingContext:
    """Tests for ProcessingContext creation and defaults."""

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
        assert ctx.whisper_model == "auto"  # 默认使用 auto（固定 Large V3）

    def test_processing_context_with_all_params(self):
        """Test ProcessingContext with explicit parameter values."""
        ctx = ProcessingContext(
            video_path="/test/movie.mkv",
            audio_path="/test/audio.wav",
            src_lang="en",
            tgt_lang="ja",
            whisper_model="large-v3",
            whisper_device="cpu",
            translation_model="facebook/m2m100_1.2B",
            use_local_models_only=True,
            bilingual=True,
            bilingual_layout="source_on_top",
            style_preset="anime",
        )
        assert ctx.video_path == "/test/movie.mkv"
        assert ctx.audio_path == "/test/audio.wav"
        assert ctx.src_lang == "en"
        assert ctx.tgt_lang == "ja"
        assert ctx.whisper_model == "large-v3"
        assert ctx.whisper_device == "cpu"
        assert ctx.translation_model == "facebook/m2m100_1.2B"
        assert ctx.use_local_models_only is True
        assert ctx.bilingual is True
        assert ctx.bilingual_layout == "source_on_top"
        assert ctx.style_preset == "anime"

    def test_processing_context_none_video_path(self):
        """Test ProcessingContext with no video_path (audio-only mode)."""
        ctx = ProcessingContext(audio_path="/test/audio.mp3")
        assert ctx.video_path is None
        assert ctx.audio_path == "/test/audio.mp3"

    def test_is_cancelled_no_callback(self):
        """is_cancelled returns False when no progress_callback is set."""
        ctx = ProcessingContext()
        assert ctx.is_cancelled() is False

    def test_is_cancelled_no_gui_observers(self):
        """is_cancelled returns False when gui_observers is None."""
        ctx = ProcessingContext(gui_observers=None)
        assert ctx.is_cancelled() is False

    def test_is_cancelled_via_progress_callback(self):
        """is_cancelled delegates to progress_callback.is_cancelled()."""

        class FakeCallback:
            def is_cancelled(self):
                return True

            def update(self, progress, message):
                pass

        ctx = ProcessingContext(progress_callback=FakeCallback())
        assert ctx.is_cancelled() is True

    def test_is_cancelled_via_gui_observers(self):
        """is_cancelled delegates to gui_observers['cancelled']()."""
        ctx = ProcessingContext(gui_observers={"cancelled": lambda: True})
        assert ctx.is_cancelled() is True

    def test_is_cancelled_gui_observers_no_cancelled_key(self):
        """is_cancelled returns False when gui_observers lacks 'cancelled' key."""
        ctx = ProcessingContext(gui_observers={"other": lambda: True})
        assert ctx.is_cancelled() is False

    def test_update_progress_with_callback(self):
        """update_progress delegates to progress_callback.update()."""
        updated = {}

        class FakeCallback:
            def is_cancelled(self):
                return False

            def update(self, progress, message):
                updated["progress"] = progress
                updated["message"] = message

            def set_stage(self, stage):
                updated["stage"] = stage

        ctx = ProcessingContext(progress_callback=FakeCallback())
        ctx.update_progress("transcription", 50.0, "Processing...")
        assert updated["progress"] == 50.0
        assert updated["message"] == "Processing..."
        assert ctx.get_stage() == "transcription"

    def test_update_progress_via_gui_observers(self):
        """update_progress calls gui_observers stage-specific callback."""
        updated = {}

        ctx = ProcessingContext(
            gui_observers={
                "transcription_progress_func": lambda p, m: updated.update(
                    {"progress": p, "message": m}
                )
            }
        )
        ctx.update_progress("transcription", 75.0, "Halfway")
        assert updated["progress"] == 75.0
        assert updated["message"] == "Halfway"

    def test_update_progress_no_callback_no_observers(self):
        """update_progress still sets stage even without callback or observers."""
        ctx = ProcessingContext()
        ctx.update_progress("translation", 80.0, "Translating")
        assert ctx.get_stage() == "translation"

    def test_set_and_get_stage(self):
        """set_stage / get_stage round-trip."""
        ctx = ProcessingContext()
        assert ctx.get_stage() == "model_loading"
        ctx.set_stage("audio_extraction")
        assert ctx.get_stage() == "audio_extraction"

    def test_get_video_name_from_video_path(self):
        """get_video_name returns stem of video_path."""
        ctx = ProcessingContext(video_path="/data/movies/demo.mp4")
        assert ctx.get_video_name() == "demo"

    def test_get_video_name_fallback_to_audio_path(self):
        """get_video_name falls back to audio_path stem."""
        ctx = ProcessingContext(audio_path="/data/audio/podcast.wav")
        assert ctx.get_video_name() == "podcast"

    def test_get_video_name_no_paths(self):
        """get_video_name returns 'output' when no paths set."""
        ctx = ProcessingContext()
        assert ctx.get_video_name() == "output"

    def test_get_video_dir_from_video_path(self):
        """get_video_dir returns parent dir of video_path."""
        ctx = ProcessingContext(video_path="/data/movies/demo.mp4")
        assert ctx.get_video_dir() == "/data/movies"

    def test_get_video_dir_fallback_to_audio_path(self):
        """get_video_dir falls back to audio_path parent."""
        ctx = ProcessingContext(audio_path="/data/audio/podcast.wav")
        assert ctx.get_video_dir() == "/data/audio"

    def test_get_video_dir_no_paths(self):
        """get_video_dir returns '.' when no paths set."""
        ctx = ProcessingContext()
        assert ctx.get_video_dir() == "."


class TestProcessingResult:
    """Tests for ProcessingResult creation and from_exception."""

    def test_success_result(self):
        """Test creating a successful ProcessingResult."""
        result = ProcessingResult(success=True, output_path="/out/subs.srt")
        assert result.success is True
        assert result.output_path == "/out/subs.srt"
        assert result.error_message == ""
        assert result.error_type is None

    def test_failure_result(self):
        """Test creating a failed ProcessingResult directly."""
        result = ProcessingResult(
            success=False, error_message="Something broke", error_type="RuntimeError"
        )
        assert result.success is False
        assert result.error_message == "Something broke"
        assert result.error_type == "RuntimeError"

    def test_from_exception_generic(self):
        """from_exception with a generic Exception."""
        exc = ValueError("bad value")
        result = ProcessingResult.from_exception(exc)
        assert result.success is False
        assert result.error_message == "bad value"
        assert result.error_type == "ValueError"
        assert result.error_severity is None
        assert result.error_context is None

    def test_from_exception_media_factory_error(self):
        """from_exception with MediaFactoryError populates severity and context."""
        exc = ProcessingError(
            message="Transcription failed",
            context={"file": "a.mp4"},
            severity="recoverable",
        )
        result = ProcessingResult.from_exception(exc)
        assert result.success is False
        assert result.error_message == "Transcription failed"
        assert result.error_type == "ProcessingError"
        assert result.error_severity == "recoverable"
        assert result.error_context == {"file": "a.mp4"}

    def test_from_exception_configuration_error(self):
        """from_exception with ConfigurationError (default severity is fatal)."""
        exc = ConfigurationError("Missing config")
        result = ProcessingResult.from_exception(exc)
        assert result.success is False
        assert result.error_message == "Missing config"
        assert result.error_type == "ConfigurationError"
        assert result.error_severity == "fatal"

    def test_from_exception_preserves_context(self):
        """from_exception attaches the ProcessingContext when provided."""
        ctx = ProcessingContext(video_path="/test/v.mp4")
        exc = RuntimeError("boom")
        result = ProcessingResult.from_exception(exc, context=ctx)
        assert result.context is ctx

    def test_from_exception_media_factory_error_no_context(self):
        """from_exception with MediaFactoryError that has empty context dict."""
        exc = MediaFactoryError("plain error")
        result = ProcessingResult.from_exception(exc)
        assert result.error_context == {}
        assert result.error_severity == "fatal"

    def test_default_metadata(self):
        """ProcessingResult metadata defaults to empty dict."""
        result = ProcessingResult(success=True)
        assert result.metadata == {}
