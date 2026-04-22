"""MediaFactory 自定义异常类。

提供简洁的异常层次结构，便于错误处理和用户友好的错误提示。
"""

from enum import Enum
from typing import Any, Optional


class ErrorSeverity(Enum):
    """Error severity levels for categorization."""

    FATAL = "fatal"  # Stop processing immediately
    RECOVERABLE = "recoverable"  # Can retry or use fallback
    WARNING = "warning"  # Continue with limitations


# =============================================================================
# Base Exception Class
# =============================================================================


class MediaFactoryError(Exception):
    """MediaFactory 基础异常类。

    所有 MediaFactory 特定异常的基类。
    支持错误上下文和严重性级别。
    """

    def __init__(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
        severity: str | ErrorSeverity = ErrorSeverity.FATAL,
    ):
        """初始化异常。

        Args:
            message: 错误消息
            context: 错误上下文信息（文件路径、操作等）
            severity: 错误严重程度（fatal/recoverable/warning 或 ErrorSeverity 枚举）
        """
        self.message = message
        self.context = context or {}
        # Support both string and Enum severity
        if isinstance(severity, ErrorSeverity):
            self.severity = severity.value
        else:
            self.severity = severity
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


# =============================================================================
# Core Exception Types (Simplified to 3 core types)
# =============================================================================


class ProcessingError(MediaFactoryError):
    """处理阶段异常。

    所有处理错误的通用异常（音频提取、转录、翻译、字幕生成、API调用、网络、设备等）。
    默认严重程度：recoverable（可重试或使用后备方案）。
    """

    def __init__(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
        severity: str | ErrorSeverity = ErrorSeverity.RECOVERABLE,
    ):
        super().__init__(message, context, severity)


class ConfigurationError(MediaFactoryError):
    """配置异常。

    配置文件、配置参数、验证错误、认证错误等相关问题。
    默认严重程度：fatal（无法继续执行）。
    """

    def __init__(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
        severity: str | ErrorSeverity = ErrorSeverity.FATAL,
    ):
        super().__init__(message, context, severity)


class OperationCancelledError(MediaFactoryError):
    """User or system cancellation.

    Operation was intentionally cancelled.
    Default severity: warning (not an error, but informative).
    """

    def __init__(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
        severity: str | ErrorSeverity = ErrorSeverity.WARNING,
    ):
        super().__init__(message, context, severity)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Error severity
    "ErrorSeverity",
    # Base exception
    "MediaFactoryError",
    # Core exceptions (3 types)
    "ProcessingError",
    "ConfigurationError",
    "OperationCancelledError",
]
