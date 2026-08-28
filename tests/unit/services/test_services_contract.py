"""services 层契约测试。

锁定各 service 的编排行为（上下文组装、Pipeline 委托、结果映射），
为 Phase 3 结构性收敛提供安全网。全部 mock，不触碰真实引擎。
"""

import asyncio

import pytest

from mediafactory.core.progress_protocol import NO_OP_PROGRESS
from mediafactory.pipeline.context import ProcessingResult

pytestmark = [pytest.mark.unit]


def run(coro):
    return asyncio.run(coro)


class FakeAudioEngine:
    """AudioEngine 替身：记录 extract 收到的路径与参数。"""

    calls = []

    def extract(self, video_path, **kwargs):
        type(self).calls.append((video_path, kwargs))
        return "out/audio.wav"


class FakeDefaultPipeline:
    """替身 Pipeline：记录上下文与工厂收到的四个引擎。"""

    last_context = None
    received_engines = None

    @classmethod
    def create_default(cls, audio, recognition, translation, srt):
        cls.received_engines = (audio, recognition, translation, srt)
        return cls()

    def execute(self, context):
        type(self).last_context = context
        context.output_path = "out/sub.srt"
        return ProcessingResult(success=True, output_path="out/sub.srt")


class FakeTranslationPipeline:
    """替身 Pipeline：记录 create_translation_only 的参数与上下文。"""

    last_context = None
    received_args = None

    @classmethod
    def create_translation_only(cls, translation_engine, srt_engine):
        cls.received_args = (translation_engine, srt_engine)
        return cls()

    def execute(self, context):
        type(self).last_context = context
        return ProcessingResult(success=True, output_path="out/translated.ass")


class FakeEngine:
    """轻量引擎替身（避免真实引擎初始化）。"""


class RecordingTranslationEngine:
    """TranslationEngine 替身工厂：记录每次实例化，用于验证引擎传递链路。"""

    instances = []

    def __init__(self, *args, **kwargs):
        type(self).instances.append(self)


class FakeSRTEngine:
    """SRTEngine 替身：parse 返回固定非空 segments。"""

    stub_segments = [{"start": 0.0, "end": 1.5, "text": "hello"}]

    def parse(self, path):
        return list(type(self).stub_segments)


class FakeLocalEngine:
    """本地翻译引擎替身：记录调用并回显翻译。"""

    calls = []

    def translate(self, wrapped, src, tgt):
        type(self).calls.append((wrapped, src, tgt))
        return {"segments": [{"text": f"[{tgt}] {wrapped['segments'][0]['text']}"}]}


class FakeEnhancementEngine:
    """VideoEnhancementEngine 替身：记录构造配置与 enhance 调用。"""

    instances = []
    enhance_calls = []
    last_config = None

    def __init__(self, config):
        type(self).instances.append(self)
        type(self).last_config = config

    def enhance(self, video_path, output_path, progress=None):
        type(self).enhance_calls.append((video_path, output_path))
        return "out/v_enhanced.mp4"


@pytest.fixture(autouse=True)
def reset_fake_state():
    """每个测试前重置替身的共享类状态，避免跨测试泄漏。"""
    FakeAudioEngine.calls.clear()
    FakeDefaultPipeline.last_context = None
    FakeDefaultPipeline.received_engines = None
    FakeTranslationPipeline.last_context = None
    FakeTranslationPipeline.received_args = None
    FakeEnhancementEngine.instances.clear()
    FakeEnhancementEngine.enhance_calls.clear()
    FakeLocalEngine.calls.clear()
    RecordingTranslationEngine.instances.clear()
    yield


class TestAudioService:
    def test_extract_audio_delegates_to_engine_with_kwargs(self, monkeypatch):
        from mediafactory.services import audio as audio_module
        from mediafactory.services.audio import AudioService

        monkeypatch.setattr(audio_module, "AudioEngine", FakeAudioEngine)

        result = run(
            AudioService().extract_audio(
                video_path="v.mp4",
                sample_rate=44100,
                channels=1,
                output_format="mp3",
                progress=NO_OP_PROGRESS,
            )
        )

        assert result.success is True
        assert result.output_path == "out/audio.wav"
        # 契约：参数原样映射给引擎，未指定的保持 None/默认语义
        video_path, kwargs = FakeAudioEngine.calls[0]
        assert video_path.endswith("v.mp4")
        assert kwargs["sample_rate"] == 44100
        assert kwargs["channels"] == 1
        assert kwargs["output_format"] == "mp3"
        assert kwargs["filter_enabled"] is True
        assert kwargs["output_path"] is None

    def test_extract_audio_engine_failure_maps_to_result(self, monkeypatch):
        from mediafactory.services import audio as audio_module
        from mediafactory.services.audio import AudioService

        class BrokenAudioEngine:
            def extract(self, video_path, **kwargs):
                raise RuntimeError("ffmpeg failed")

        monkeypatch.setattr(audio_module, "AudioEngine", BrokenAudioEngine)

        result = run(AudioService().extract_audio("v.mp4", progress=NO_OP_PROGRESS))

        assert result.success is False
        assert result.error_type == "RuntimeError"


class TestSubtitleService:
    def test_generate_subtitle_local_mode_uses_default_pipeline(self, monkeypatch):
        from mediafactory.services import subtitle as sub_module
        from mediafactory.services.subtitle import SubtitleService

        monkeypatch.setattr(sub_module, "Pipeline", FakeDefaultPipeline)
        for name in ("AudioEngine", "RecognitionEngine", "SRTEngine"):
            monkeypatch.setattr(sub_module, name, FakeEngine)
        monkeypatch.setattr(
            sub_module, "TranslationEngine", RecordingTranslationEngine
        )

        service = SubtitleService()
        result = run(
            service.generate_subtitle(
                video_path="v.mp4",
                source_lang="en",
                target_lang="zh",
                use_llm=False,
                output_format="ass",
                progress=NO_OP_PROGRESS,
            )
        )

        assert result.success is True
        assert result.output_path == "out/sub.srt"
        # 契约：四个引擎按位传入，缓存的引擎与本次构造的翻译引擎各归其位
        received = FakeDefaultPipeline.received_engines
        assert received is not None
        audio, recognition, translation, srt = received
        assert audio is service._audio_engine
        assert recognition is service._recognition_engine
        assert srt is service._srt_engine
        assert translation is RecordingTranslationEngine.instances[0]
        ctx = FakeDefaultPipeline.last_context
        assert ctx is not None
        assert ctx.src_lang == "en"
        assert ctx.tgt_lang == "zh"
        assert ctx.config["output_format"] == "ass"
        assert ctx.config["output_format_type"] == "ass"

    def test_generate_subtitle_llm_unavailable_falls_back_to_local(self, monkeypatch):
        from mediafactory.services import subtitle as sub_module
        from mediafactory.services.subtitle import SubtitleService

        monkeypatch.setattr(sub_module, "Pipeline", FakeDefaultPipeline)
        for name in ("AudioEngine", "RecognitionEngine", "SRTEngine"):
            monkeypatch.setattr(sub_module, name, FakeEngine)
        monkeypatch.setattr(
            sub_module, "TranslationEngine", RecordingTranslationEngine
        )
        # LLM 后端初始化失败 → 应回退本地引擎（不抛异常）
        monkeypatch.setattr(
            sub_module, "initialize_llm_backend", lambda *a, **k: None
        )

        result = run(
            SubtitleService().generate_subtitle(
                "v.mp4", use_llm=True, progress=NO_OP_PROGRESS
            )
        )
        assert result.success is True
        # 契约：回退时新建的本地翻译引擎被原样传给 Pipeline（第 3 位）
        received = FakeDefaultPipeline.received_engines
        assert received is not None
        assert received[2] is RecordingTranslationEngine.instances[0]


class TestTranslationService:
    def test_translate_text_local_wraps_and_unwraps_segments(self, monkeypatch):
        from mediafactory.services.translation import TranslationService

        service = TranslationService()
        monkeypatch.setattr(service, "_local_engine", FakeLocalEngine())

        result = run(service.translate_text("hello", target_lang="zh"))

        assert result.success is True
        assert result.metadata["translated_text"] == "[zh] hello"
        assert result.metadata["original_text"] == "hello"
        # 契约：本地引擎收到的必须是 segments 包装格式，源语言 auto
        assert len(FakeLocalEngine.calls) == 1
        wrapped, src, tgt = FakeLocalEngine.calls[0]
        assert wrapped == {"segments": [{"text": "hello"}]}
        assert src == "auto"
        assert tgt == "zh"

    def test_translate_text_exception_returns_failure_result(self, monkeypatch):
        from mediafactory.services.translation import TranslationService

        class BrokenEngine:
            def translate(self, wrapped, src, tgt):
                raise RuntimeError("model not loaded")

        service = TranslationService()
        monkeypatch.setattr(service, "_local_engine", BrokenEngine())

        result = run(service.translate_text("hello", target_lang="zh"))

        assert result.success is False
        assert result.error_type == "RuntimeError"

    def test_translate_srt_builds_context_and_delegates_to_pipeline(self, monkeypatch):
        from mediafactory.services import translation as tr_module
        from mediafactory.services.translation import TranslationService

        monkeypatch.setattr(tr_module, "Pipeline", FakeTranslationPipeline)
        monkeypatch.setattr(tr_module, "SRTEngine", FakeSRTEngine)
        monkeypatch.setattr(tr_module, "TranslationEngine", FakeEngine)

        result = run(
            TranslationService().translate_srt(
                "in/sub.srt",
                target_lang="ja",
                output_format="ass",
                progress=NO_OP_PROGRESS,
            )
        )

        assert result.success is True
        assert result.output_path == "out/translated.ass"
        # 契约：create_translation_only 被调用
        assert FakeTranslationPipeline.received_args is not None
        ctx = FakeTranslationPipeline.last_context
        assert ctx is not None
        # 契约：parse 出的 segments 注入 transcription_result
        assert ctx.transcription_result == {"segments": FakeSRTEngine.stub_segments}
        assert ctx.tgt_lang == "ja"
        # 契约：输出路径语义 .{target_lang}{ext}
        assert ctx.config["output_path"] == "in/sub.ja.ass"
        assert ctx.config["output_format_type"] == "ass"

    def test_translate_srt_empty_segments_returns_validation_error(self, monkeypatch):
        from mediafactory.services import translation as tr_module
        from mediafactory.services.translation import TranslationService

        class EmptySRTEngine:
            def parse(self, path):
                return []

        monkeypatch.setattr(tr_module, "Pipeline", FakeTranslationPipeline)
        monkeypatch.setattr(tr_module, "SRTEngine", EmptySRTEngine)
        monkeypatch.setattr(tr_module, "TranslationEngine", FakeEngine)

        result = run(
            TranslationService().translate_srt(
                "in/sub.srt", target_lang="ja", progress=NO_OP_PROGRESS
            )
        )

        assert result.success is False
        assert result.error_type == "ValidationError"
        # 契约：空 segments 提前返回，不创建 Pipeline
        assert FakeTranslationPipeline.received_args is None


class TestTranscriptionService:
    def test_transcribe_builds_context_and_uses_standalone_pipeline(self, monkeypatch):
        from mediafactory.services import transcription as tr_module
        from mediafactory.services.transcription import TranscriptionService

        class FakeStandalonePipeline:
            last_context = None
            received_args = None

            @classmethod
            def create_transcribe_standalone(cls, recognition_engine, srt_engine):
                cls.received_args = (recognition_engine, srt_engine)
                return cls()

            def execute(self, context):
                type(self).last_context = context
                context.output_path = "out/sub.srt"
                return ProcessingResult(success=True, output_path="out/sub.srt")

        monkeypatch.setattr(tr_module, "Pipeline", FakeStandalonePipeline)
        monkeypatch.setattr(tr_module, "RecognitionEngine", FakeEngine)
        monkeypatch.setattr(tr_module, "SRTEngine", FakeEngine)

        service = TranscriptionService()
        result = run(
            service.transcribe("a.mp3", language="en", output_format="ass", progress=NO_OP_PROGRESS)
        )

        assert result.success is True
        assert result.output_path == "out/sub.srt"
        received = FakeStandalonePipeline.received_args
        assert received is not None
        assert received[0] is service._recognition_engine  # 缓存引擎原样传递
        ctx = FakeStandalonePipeline.last_context
        assert ctx is not None
        assert ctx.audio_path.endswith("a.mp3")
        assert ctx.src_lang == "en"  # 非 auto 时保留
        assert ctx.config["output_format_type"] == "ass"

    def test_transcribe_auto_language_becomes_none(self, monkeypatch):
        from mediafactory.services import transcription as tr_module
        from mediafactory.services.transcription import TranscriptionService

        class FakeStandalonePipeline:
            last_context = None

            @classmethod
            def create_transcribe_standalone(cls, recognition_engine, srt_engine):
                return cls()

            def execute(self, context):
                type(self).last_context = context
                return ProcessingResult(success=True, output_path="out.srt")

        monkeypatch.setattr(tr_module, "Pipeline", FakeStandalonePipeline)
        monkeypatch.setattr(tr_module, "RecognitionEngine", FakeEngine)
        monkeypatch.setattr(tr_module, "SRTEngine", FakeEngine)

        run(TranscriptionService().transcribe("a.mp3", language="auto", progress=NO_OP_PROGRESS))

        ctx = FakeStandalonePipeline.last_context
        assert ctx is not None
        assert ctx.src_lang is None  # auto → None（引擎据此自动检测）


class TestVideoEnhancementService:
    def test_enhance_builds_config_and_delegates_to_engine(self, monkeypatch):
        from mediafactory.services.video_enhancement import VideoEnhancementService

        monkeypatch.setattr(
            "mediafactory.engine.video_enhancement.VideoEnhancementEngine",
            FakeEnhancementEngine,
        )

        result = run(
            VideoEnhancementService().enhance(
                "v.mp4", scale=4, model_type="anime", denoise=True, temporal=True,
                progress=NO_OP_PROGRESS,
            )
        )

        assert result.success is True
        assert result.output_path == "out/v_enhanced.mp4"
        # 契约：参数映射进 EnhancementConfig
        config = FakeEnhancementEngine.last_config
        assert config is not None
        assert config.scale == 4
        assert config.model_type == "anime"
        assert config.denoise is True
        assert config.temporal is True
        # 契约：引擎收到视频路径与输出路径
        video_path, output_path = FakeEnhancementEngine.enhance_calls[-1]
        assert video_path.endswith("v.mp4")
        assert output_path.endswith("v_enhanced.mp4")

    def test_enhance_default_output_path_suffix(self, monkeypatch):
        from mediafactory.services.video_enhancement import VideoEnhancementService

        monkeypatch.setattr(
            "mediafactory.engine.video_enhancement.VideoEnhancementEngine",
            FakeEnhancementEngine,
        )

        run(VideoEnhancementService().enhance("dir/clip.mp4", progress=NO_OP_PROGRESS))

        # 契约：未指定输出路径时自动追加 _enhanced 后缀
        _, output_path = FakeEnhancementEngine.enhance_calls[-1]
        assert output_path.endswith("clip_enhanced.mp4")
