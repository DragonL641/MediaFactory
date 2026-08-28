"""Pipeline 取消语义回归测试。

取消信号（OperationCancelledError）在 stage 内抛出时必须终止流水线，
不得被当作"带警告完成"继续执行。
"""

import pytest

from mediafactory.exceptions import OperationCancelledError
from mediafactory.pipeline.context import ProcessingContext
from mediafactory.pipeline.pipeline import Pipeline
from mediafactory.pipeline.stage import ProcessingStage

pytestmark = [pytest.mark.unit]


class CancelStage(ProcessingStage):
    """execute 时抛出取消异常的假 stage。"""

    name = "cancel_stage"

    def should_execute(self, ctx: ProcessingContext) -> bool:
        return True

    def execute(self, ctx: ProcessingContext) -> ProcessingContext:
        raise OperationCancelledError(message="cancelled inside stage")


class NoopStage(ProcessingStage):
    """什么都不做的假 stage，记录是否被执行。"""

    name = "noop_stage"

    def __init__(self):
        self.executed = False

    def should_execute(self, ctx: ProcessingContext) -> bool:
        return True

    def execute(self, ctx: ProcessingContext) -> ProcessingContext:
        self.executed = True
        return ctx


class TestPipelineCancellation:
    def test_cancel_in_middle_stage_stops_pipeline(self):
        """中间 stage 取消：后续 stage 不得执行，结果为失败"""
        noop = NoopStage()
        pipeline = Pipeline([CancelStage(), noop])

        result = pipeline.execute(ProcessingContext(video_path="x.mp4"))

        assert result.success is False
        assert result.error_type == "OperationCancelledError"
        assert noop.executed is False

    def test_cancel_in_last_stage_is_not_success(self):
        """最后一个 stage 取消：不得返回 success=True（当前 bug）"""
        pipeline = Pipeline([NoopStage(), CancelStage()])

        result = pipeline.execute(ProcessingContext(video_path="x.mp4"))

        assert result.success is False
        assert result.error_type == "OperationCancelledError"
