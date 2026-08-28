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


class FakeAudioPipeline:
    """替身 Pipeline：记录上下文与工厂收到的引擎。"""

    last_context = None
    received_engine = None

    @classmethod
    def create_audio_only(cls, engine):
        cls.received_engine = engine
        return cls()

    def execute(self, context):
        type(self).last_context = context
        context.audio_path = "out/audio.wav"
        return ProcessingResult(success=True, output_path="out/audio.wav")


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


@pytest.fixture(autouse=True)
def reset_fake_state():
    """每个测试前重置替身的共享类状态，避免跨测试泄漏。"""
    FakeAudioPipeline.last_context = None
    FakeAudioPipeline.received_engine = None
    FakeDefaultPipeline.last_context = None
    FakeDefaultPipeline.received_engines = None
    FakeTranslationPipeline.last_context = None
    FakeTranslationPipeline.received_args = None
    FakeLocalEngine.calls.clear()
    RecordingTranslationEngine.instances.clear()
    yield


class TestAudioService:
    def test_extract_audio_builds_context_and_maps_result(self, monkeypatch):
        from mediafactory.services import audio as audio_module
        from mediafactory.services.audio import AudioService

        monkeypatch.setattr(audio_module, "Pipeline", FakeAudioPipeline)
        monkeypatch.setattr(audio_module, "AudioEngine", FakeEngine)

        service = AudioService()
        result = run(
            service.extract_audio(
                video_path="v.mp4",
                sample_rate=44100,
                channels=1,
                output_format="mp3",
                progress=NO_OP_PROGRESS,
            )
        )

        assert result.success is True
        assert result.output_path == "out/audio.wav"
        # 契约：Pipeline 收到的是 service 持有的同一引擎实例
        assert FakeAudioPipeline.received_engine is service._audio_engine
        ctx = FakeAudioPipeline.last_context
        assert ctx is not None
        assert ctx.video_path.endswith("v.mp4")
        assert ctx.config["sample_rate"] == 44100
        assert ctx.config["channels"] == 1
        assert ctx.config["output_format"] == "mp3"

    def test_extract_audio_maps_pipeline_failure(self, monkeypatch):
        from mediafactory.services import audio as audio_module
        from mediafactory.services.audio import AudioService

        class FailingPipeline(FakeAudioPipeline):
            def execute(self, context):
                return ProcessingResult(
                    success=False, error_message="boom", error_type="ProcessingError"
                )

        monkeypatch.setattr(audio_module, "Pipeline", FailingPipeline)
        monkeypatch.setattr(audio_module, "AudioEngine", FakeEngine)

        result = run(
            AudioService().extract_audio("v.mp4", progress=NO_OP_PROGRESS)
        )

        assert result.success is False
        assert result.error_message == "boom"


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
