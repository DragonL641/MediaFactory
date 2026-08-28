"""Pipeline 进度区间映射测试。

锁定：stage 内 0-100 进度按该 pipeline 的权重组合映射到全局 0-100 区间，
短流程（如 translation-only）不再从固定 70% 起跳。
"""

import pytest

from mediafactory.exceptions import OperationCancelledError
from mediafactory.pipeline.context import ProcessingContext
from mediafactory.pipeline.pipeline import Pipeline, _StageProgress
from mediafactory.pipeline.stage import ProcessingStage

pytestmark = [pytest.mark.unit]


class RecordingCallback:
    def __init__(self):
        self.calls = []
        self.stage = None

    def set_stage(self, stage):
        self.stage = stage

    def update(self, progress, message=""):
        self.calls.append((self.stage, progress, message))

    def is_cancelled(self):
        return False


class _NamedStage(ProcessingStage):
    def __init__(self, name):
        self.name = name

    def execute(self, ctx):
        # 模拟真实 stage 的 _begin：先设置阶段名再报告进度
        ctx.set_stage(self.name)
        ctx.progress_callback.update(50.0, "half")
        return ctx


class TestProgressMapping:
    def test_single_stage_pipeline_maps_linearly(self):
        cb = RecordingCallback()
        ctx = ProcessingContext(video_path="v.mp4", progress_callback=cb)
        Pipeline([_NamedStage("transcription")]).execute(ctx)
        # 唯一 stage 权重归一化后占 0-100：50% → 50
        assert any(abs(p - 50.0) < 0.01 for _, p, _ in cb.calls)

    def test_translation_only_starts_from_zero(self):
        cb = RecordingCallback()
        ctx = ProcessingContext(video_path="v.srt", progress_callback=cb)
        pipeline = Pipeline([_NamedStage("translation"), _NamedStage("srt_generation")])
        pipeline.execute(ctx)
        # translation 权重 25、srt 5 → 区间 [0, 83.3) 与 [83.3, 100]
        boundary = 100.0 / 30.0 * 25.0
        translation_values = [p for s, p, _ in cb.calls if s == "translation"]
        srt_values = [p for s, p, _ in cb.calls if s == "srt_generation"]
        assert translation_values and srt_values
        assert min(translation_values) >= 0.0
        assert max(translation_values) <= boundary + 0.01
        assert min(srt_values) >= boundary - 0.01

    def test_default_pipeline_translation_window_approx_70_95(self):
        from mediafactory.engine.audio import AudioEngine
        from mediafactory.engine.recognition import RecognitionEngine
        from mediafactory.engine.srt import SRTEngine
        from mediafactory.engine.translation import TranslationEngine

        pipeline = Pipeline.create_default(
            AudioEngine(), RecognitionEngine(), TranslationEngine(), SRTEngine()
        )
        # 只验证区间计算，不 execute（无真实模型会在 model_loading 抛错）
        ranges = pipeline._compute_ranges()
        t_start, t_end = ranges["translation"]
        assert abs(t_start - 70.0) < 2.0
        assert abs(t_end - 95.0) < 1.0

    def test_cancel_delegates_through_mapper(self):
        class CancelOnUpdateCallback(RecordingCallback):
            """update 后置取消：循环级检查先通过，取消只能经映射器委托发现。"""

            def __init__(self):
                super().__init__()
                self._cancelled = False

            def update(self, progress, message=""):
                super().update(progress, message)
                self._cancelled = True

            def is_cancelled(self):
                return self._cancelled

        class CancellingStage(ProcessingStage):
            name = "postprocess"

            def execute(self, ctx):
                ctx.set_stage(self.name)
                ctx.progress_callback.update(10.0, "working")
                if ctx.progress_callback.is_cancelled():
                    raise OperationCancelledError(message="cancelled during stage")
                return ctx

        cb = CancelOnUpdateCallback()
        ctx = ProcessingContext(video_path="v.mp4", progress_callback=cb)
        result = Pipeline([CancellingStage()]).execute(ctx)
        # update 经映射器到达底层回调，is_cancelled 经映射器委托返回 True
        assert cb.calls
        assert result.success is False
        assert result.error_type == "OperationCancelledError"

    def test_stage_progress_maps_values(self):
        cb = RecordingCallback()
        mapper = _StageProgress(cb, 70.0, 95.0)
        mapper.update(50.0, "half")
        assert abs(cb.calls[-1][1] - 82.5) < 0.01

    def test_unknown_stage_name_gets_unit_weight(self):
        pipeline = Pipeline([_NamedStage("weird_stage"), _NamedStage("transcription")])
        ranges = pipeline._compute_ranges()
        w_start, w_end = ranges["weird_stage"]
        # 未知名默认权重 1，与 transcription 40 归一后占 1/41
        assert abs((w_end - w_start) - 100.0 / 41.0) < 0.01

    def test_stage_wrappers_do_not_stack_across_stages(self):
        """连续多个 stage 不得叠加映射：每个映射器都基于原始回调。"""
        cb = RecordingCallback()
        ctx = ProcessingContext(video_path="v.mp4", progress_callback=cb)
        Pipeline([_NamedStage("transcription"), _NamedStage("postprocess")]).execute(
            ctx
        )
        # postprocess 区间 [80, 100]：50% → 90；若叠加映射（基于上一映射器再包装）会得到 72
        post_values = [p for s, p, _ in cb.calls if s == "postprocess"]
        assert post_values
        assert abs(post_values[-1] - 90.0) < 0.01

    def test_original_callback_restored_after_execute(self):
        cb = RecordingCallback()
        ctx = ProcessingContext(video_path="v.mp4", progress_callback=cb)
        Pipeline([_NamedStage("transcription")]).execute(ctx)
        # 结束后上下文恢复原始回调，复用 context 不会二次包装
        assert ctx.progress_callback is cb
