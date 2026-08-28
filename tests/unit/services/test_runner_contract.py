"""runner 层契约测试。

锁定统一执行入口的编排行为：ProcessingContext 组装、Pipeline 工厂参数绑定、
引擎直调参数传递、LLM 降级、segments 包装协议、readiness 门。
为结构性重构提供安全网。全部 mock，不触碰真实引擎。
"""

import asyncio

import pytest

from mediafactory.api.schemas import (
    AudioConfig,
    SubtitleConfig,
    TaskConfig,
    TaskType,
)
from mediafactory.core.progress_protocol import NO_OP_PROGRESS
from mediafactory.exceptions import ConfigurationError
from mediafactory.pipeline.context import ProcessingResult
from mediafactory.services import runner as runner_module
from mediafactory.services.runner import (
    RUNNERS,
    run_audio,
    run_subtitle,
    run_transcribe,
    run_translate,
)

pytestmark = [pytest.mark.unit]


def run(coro):
    return asyncio.run(coro)


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


class FakeStandalonePipeline:
    """替身 Pipeline：记录 create_transcribe_standalone 的参数与上下文。"""

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


class FakeAudioEngine:
    """AudioEngine 替身：记录 extract 收到的路径与参数。"""

    instances = []
    extract_calls = []

    def __init__(self):
        type(self).instances.append(self)

    def extract(self, video_path, **kwargs):
        type(self).extract_calls.append((video_path, kwargs))
        return "out/audio.wav"


class FakeRecognitionEngine:
    """RecognitionEngine 替身：记录实例化。"""

    instances = []

    def __init__(self):
        type(self).instances.append(self)


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
    """每个测试前重置替身状态与 runner 模块级引擎缓存（隔离测试）。"""
    FakeDefaultPipeline.last_context = None
    FakeDefaultPipeline.received_engines = None
    FakeStandalonePipeline.last_context = None
    FakeStandalonePipeline.received_args = None
    FakeTranslationPipeline.last_context = None
    FakeTranslationPipeline.received_args = None
    FakeAudioEngine.instances.clear()
    FakeAudioEngine.extract_calls.clear()
    FakeRecognitionEngine.instances.clear()
    RecordingTranslationEngine.instances.clear()
    FakeLocalEngine.calls.clear()
    # runner 模块级引擎缓存重置：monkeypatch 引擎类后重新触发懒加载的关键
    runner_module._audio_engine = None
    runner_module._recognition_engine = None
    runner_module._srt_engine = None
    runner_module._local_translation_engine = None
    runner_module._readiness_service = None
    yield


@pytest.fixture(autouse=True)
def bypass_readiness(monkeypatch):
    """默认绕过 readiness 门；需要验证门行为的测试自行覆盖。"""
    monkeypatch.setattr(runner_module, "_require_ready", lambda key: None)


def make_config(**overrides) -> TaskConfig:
    defaults = dict(task_type=TaskType.SUBTITLE, input_path="v.mp4")
    defaults.update(overrides)
    return TaskConfig(**defaults)


class TestRunSubtitle:
    def test_local_mode_builds_context_and_binds_engines(self, monkeypatch):
        monkeypatch.setattr(runner_module, "Pipeline", FakeDefaultPipeline)
        monkeypatch.setattr(runner_module, "AudioEngine", FakeAudioEngine)
        monkeypatch.setattr(runner_module, "RecognitionEngine", FakeRecognitionEngine)
        monkeypatch.setattr(runner_module, "SRTEngine", FakeSRTEngine)
        monkeypatch.setattr(
            runner_module, "TranslationEngine", RecordingTranslationEngine
        )

        result = run(
            run_subtitle(
                make_config(
                    source_lang="en",
                    target_lang="ja",
                    subtitle_config=SubtitleConfig(output_format="ass"),
                ),
                NO_OP_PROGRESS,
            )
        )

        assert result.success is True
        assert result.output_path == "out/sub.srt"
        # 契约：四个引擎按位传入 create_default，翻译位=本地缓存引擎
        received = FakeDefaultPipeline.received_engines
        assert received is not None
        audio, recognition, translation, srt = received
        assert audio is runner_module._audio_engine
        assert recognition is runner_module._recognition_engine
        assert srt is runner_module._srt_engine
        assert translation is runner_module._local_translation_engine
        ctx = FakeDefaultPipeline.last_context
        assert ctx is not None
        assert ctx.video_path == "v.mp4"
        assert ctx.src_lang == "en"
        assert ctx.tgt_lang == "ja"
        assert ctx.output_format == "ass"
        assert ctx.requested_output_path is None

    def test_subtitle_src_lang_auto_passthrough(self, monkeypatch):
        """契约：subtitle 的 src_lang 原值传递（含 auto，与旧 SubtitleService 一致）。"""
        monkeypatch.setattr(runner_module, "Pipeline", FakeDefaultPipeline)

        run(run_subtitle(make_config(source_lang="auto"), NO_OP_PROGRESS))

        ctx = FakeDefaultPipeline.last_context
        assert ctx is not None
        assert ctx.src_lang == "auto"

    def test_llm_unavailable_falls_back_to_local(self, monkeypatch):
        monkeypatch.setattr(runner_module, "Pipeline", FakeDefaultPipeline)
        monkeypatch.setattr(
            runner_module, "initialize_llm_backend", lambda *a, **k: None
        )

        result = run(run_subtitle(make_config(use_llm=True), NO_OP_PROGRESS))

        assert result.success is True
        received = FakeDefaultPipeline.received_engines
        assert received is not None
        # 契约：LLM 初始化失败回退到本地缓存引擎（第 3 位）
        assert received[2] is runner_module._local_translation_engine

    def test_readiness_gate_raises_configuration_error(self, monkeypatch):
        def raise_no_model(key):
            raise ConfigurationError(message="no model")

        monkeypatch.setattr(runner_module, "_require_ready", raise_no_model)

        with pytest.raises(ConfigurationError):
            run(run_subtitle(make_config(), NO_OP_PROGRESS))


class TestRunAudio:
    def test_direct_engine_call_with_typed_config(self, monkeypatch):
        monkeypatch.setattr(runner_module, "AudioEngine", FakeAudioEngine)

        audio_cfg = AudioConfig(sample_rate=44100, channels=1, output_format="mp3")
        result = run(
            run_audio(
                make_config(task_type=TaskType.AUDIO, audio_config=audio_cfg),
                NO_OP_PROGRESS,
            )
        )

        assert result.success is True
        assert result.output_path == "out/audio.wav"
        # 契约：类型化配置的 kwargs 原样映射给引擎
        video_path, kwargs = FakeAudioEngine.extract_calls[0]
        assert video_path == "v.mp4"
        assert kwargs["sample_rate"] == 44100
        assert kwargs["channels"] == 1
        assert kwargs["output_format"] == "mp3"
        assert kwargs["output_path"] is None


class TestRunTranscribe:
    def test_builds_context_and_uses_standalone_pipeline(self, monkeypatch):
        monkeypatch.setattr(runner_module, "Pipeline", FakeStandalonePipeline)
        monkeypatch.setattr(runner_module, "RecognitionEngine", FakeRecognitionEngine)
        monkeypatch.setattr(runner_module, "SRTEngine", FakeSRTEngine)

        result = run(
            run_transcribe(
                make_config(
                    task_type=TaskType.TRANSCRIBE,
                    input_path="a.mp3",
                    source_lang="en",
                    subtitle_config=SubtitleConfig(output_format="ass"),
                ),
                NO_OP_PROGRESS,
            )
        )

        assert result.success is True
        assert result.output_path == "out/sub.srt"
        # 契约：create_transcribe_standalone 绑定缓存的识别与字幕引擎
        received = FakeStandalonePipeline.received_args
        assert received is not None
        assert received[0] is runner_module._recognition_engine
        assert received[1] is runner_module._srt_engine
        ctx = FakeStandalonePipeline.last_context
        assert ctx is not None
        assert ctx.audio_path == "a.mp3"
        assert ctx.src_lang == "en"  # 非 auto 时保留
        assert ctx.output_format == "ass"

    def test_auto_language_becomes_none(self, monkeypatch):
        monkeypatch.setattr(runner_module, "Pipeline", FakeStandalonePipeline)

        run(
            run_transcribe(
                make_config(task_type=TaskType.TRANSCRIBE, input_path="a.mp3"),
                NO_OP_PROGRESS,
            )
        )

        ctx = FakeStandalonePipeline.last_context
        assert ctx is not None
        assert ctx.src_lang is None  # auto → None（引擎据此自动检测）


class TestRunTranslate:
    def test_text_local_wraps_and_unwraps_segments(self, monkeypatch):
        runner_module._local_translation_engine = FakeLocalEngine()

        result = run(
            run_translate(
                make_config(
                    task_type=TaskType.TRANSLATE, input_text="hello", target_lang="zh"
                ),
                NO_OP_PROGRESS,
            )
        )

        assert result.success is True
        assert result.metadata["translated_text"] == "[zh] hello"
        assert result.metadata["original_text"] == "hello"
        assert result.metadata["target_lang"] == "zh"
        # 契约：本地引擎收到的必须是 segments 包装格式，源语言 auto
        wrapped, src, tgt = FakeLocalEngine.calls[0]
        assert wrapped == {"segments": [{"text": "hello"}]}
        assert src == "auto"
        assert tgt == "zh"

    def test_srt_file_builds_translation_pipeline(self, monkeypatch):
        monkeypatch.setattr(runner_module, "Pipeline", FakeTranslationPipeline)
        monkeypatch.setattr(runner_module, "SRTEngine", FakeSRTEngine)
        monkeypatch.setattr(
            runner_module, "TranslationEngine", RecordingTranslationEngine
        )

        result = run(
            run_translate(
                make_config(
                    task_type=TaskType.TRANSLATE,
                    input_path="in/sub.srt",
                    target_lang="ja",
                    output_format="ass",
                ),
                NO_OP_PROGRESS,
            )
        )

        assert result.success is True
        assert result.output_path == "out/translated.ass"
        assert FakeTranslationPipeline.received_args is not None
        ctx = FakeTranslationPipeline.last_context
        assert ctx is not None
        # 契约：parse 出的 segments 注入 transcription_result
        assert ctx.transcription_result == {"segments": FakeSRTEngine.stub_segments}
        assert ctx.tgt_lang == "ja"
        # 契约：输出路径语义 .{target_lang}{ext}
        assert ctx.requested_output_path == "in/sub.ja.ass"
        assert ctx.output_format == "ass"

    def test_srt_file_explicit_output_path_takes_priority(self, monkeypatch):
        monkeypatch.setattr(runner_module, "Pipeline", FakeTranslationPipeline)
        monkeypatch.setattr(runner_module, "SRTEngine", FakeSRTEngine)

        run(
            run_translate(
                make_config(
                    task_type=TaskType.TRANSLATE,
                    input_path="in/sub.srt",
                    target_lang="ja",
                    output_path="custom/out.srt",
                ),
                NO_OP_PROGRESS,
            )
        )

        ctx = FakeTranslationPipeline.last_context
        assert ctx is not None
        # 契约：显式 output_path 优先于 .{target_lang}{ext} 推导
        assert ctx.requested_output_path == "custom/out.srt"

    def test_srt_file_empty_segments_returns_validation_error(self, monkeypatch):
        class EmptySRTEngine:
            def parse(self, path):
                return []

        monkeypatch.setattr(runner_module, "SRTEngine", EmptySRTEngine)
        monkeypatch.setattr(runner_module, "Pipeline", FakeTranslationPipeline)

        result = run(
            run_translate(
                make_config(
                    task_type=TaskType.TRANSLATE,
                    input_path="in/sub.srt",
                    target_lang="ja",
                ),
                NO_OP_PROGRESS,
            )
        )

        assert result.success is False
        assert result.error_type == "ValidationError"
        # 契约：空 segments 提前返回，不创建 Pipeline
        assert FakeTranslationPipeline.received_args is None

    def test_neither_path_nor_text_raises(self):
        with pytest.raises(ValueError):
            run(
                run_translate(
                    make_config(task_type=TaskType.TRANSLATE, input_path="x.bin"),
                    NO_OP_PROGRESS,
                )
            )

    def test_local_mode_checks_translation_readiness(self, monkeypatch):
        """契约：非 LLM 翻译必须过 translation_local readiness 门。"""

        def raise_no_model(key):
            assert key == "translation_local"
            raise ConfigurationError(message="no model")

        monkeypatch.setattr(runner_module, "_require_ready", raise_no_model)

        with pytest.raises(ConfigurationError):
            run(
                run_translate(
                    make_config(
                        task_type=TaskType.TRANSLATE, input_text="hello", use_llm=False
                    ),
                    NO_OP_PROGRESS,
                )
            )


class TestRunnersRegistry:
    def test_all_non_download_task_types_registered(self):
        for task_type in TaskType:
            if task_type is TaskType.DOWNLOAD:
                continue  # 下载走 download_task.py 专用通道，不经 runner
            assert task_type in RUNNERS, f"缺少 {task_type} 的 runner 注册"
