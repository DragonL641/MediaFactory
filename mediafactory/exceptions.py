"""MediaFactory 自定义异常类。

提供简洁的异常层次结构，便于错误处理和用户友好的错误提示。
"""


class MediaFactoryError(Exception):
    """MediaFactory 基础异常类。

    所有 MediaFactory 特定异常的基类，支持错误上下文。
    """

    def __init__(
        self,
        message: str,
        context: dict | None = None,
    ):
        """初始化异常。

        Args:
            message: 错误消息
            context: 错误上下文信息（文件路径、操作等）
        """
        self.message = message
        self.context = context or {}
        super().__init__(self._get_full_message())

    def _get_full_message(self) -> str:
        """构建完整的错误消息，包含所有可用信息。"""
        parts = [self.message]

        if self.context:
            context_parts = []
            for key, value in self.context.items():
                if value is not None:
                    context_parts.append(f"{key}: {value}")
            if context_parts:
                parts.append(f"Context: {', '.join(context_parts)}")

        return "\n  ".join(parts)

    def __str__(self) -> str:
        """返回格式化的错误消息。"""
        return self._get_full_message()


class ProcessingError(MediaFactoryError):
    """处理阶段异常。

    所有处理错误的通用异常（音频提取、转录、翻译、字幕生成、API调用、网络、设备等）。
    """


class ConfigurationError(MediaFactoryError):
    """配置异常。

    配置文件、配置参数、验证错误、认证错误等相关问题。
    """


class OperationCancelledError(MediaFactoryError):
    """用户或系统取消。

    操作被有意取消，不是错误。
    """
