"""处理阶段基类模块"""

from abc import ABC, abstractmethod
from .context import ProcessingContext
from ..core.progress_protocol import NO_OP_PROGRESS


class ProcessingStage(ABC):
    """处理阶段抽象基类

    生命周期：should_execute() -> execute() -> validate()
    """

    name: str = "base_stage"

    @abstractmethod
    def should_execute(self, ctx: ProcessingContext) -> bool:
        """检查是否需要执行（结果已存在可跳过）"""

    @abstractmethod
    def execute(self, ctx: ProcessingContext) -> ProcessingContext:
        """执行阶段逻辑"""

    def validate(self, ctx: ProcessingContext) -> bool:
        """验证执行结果，默认返回 True"""
        return True

    def on_error(self, ctx: ProcessingContext, error: Exception) -> Exception:
        """处理执行错误，默认重新抛出"""
        return error

    def _log(self, message: str, level: str = "info"):
        """记录日志"""
        from ..logging import log_info, log_warning, log_error, log_success

        loggers = {
            "info": log_info,
            "warning": log_warning,
            "error": log_error,
            "success": log_success,
        }
        logger = loggers.get(level, log_info)
        logger(f"[{self.name}] {message}")

    def _begin(self, ctx: ProcessingContext, display_name: str):
        """初始化阶段：记录日志、设置阶段名、获取进度回调。"""
        from ..logging import log_step

        log_step(display_name)
        ctx.set_stage(self.name)
        progress = ctx.progress_callback or NO_OP_PROGRESS
        return progress


class SkipableStage(ProcessingStage):
    """可跳过阶段基类"""

    def should_execute(self, ctx: ProcessingContext) -> bool:
        """默认始终执行，子类可覆盖"""
        return True
