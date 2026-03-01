"""MediaFactory 自定义异常类。

提供简洁的异常层次结构，便于错误处理和用户友好的错误提示。
重试机制使用 tenacity 库实现。
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Callable, TypeVar

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryCallState,
)

from mediafactory.logging import log_debug


T = TypeVar("T")


class ErrorSeverity(Enum):
    """Error severity levels for categorization."""

    FATAL = "fatal"  # Stop processing immediately
    RECOVERABLE = "recoverable"  # Can retry or use fallback
    WARNING = "warning"  # Continue with limitations


# =============================================================================
# Retry Mechanism (using tenacity)
# =============================================================================

# Exception types that are typically retryable
RETRYABLE_EXCEPTIONS = (
    TimeoutError,
    ConnectionError,
    ConnectionRefusedError,
    ConnectionResetError,
)


@dataclass
class RetryConfig:
    """Configuration for retry mechanism.

    Attributes:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        max_delay: Maximum delay between retries (cap)
        on_retry: Optional callback called before each retry
    """

    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    on_retry: Optional[Callable[[int, Exception], None]] = None


def _log_retry(retry_state: RetryCallState) -> None:
    """Log retry attempt for debugging."""
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    log_debug(
        f"Retry: Attempt {retry_state.attempt_number} failed: {exc}. " f"Retrying..."
    )


def retry_on_api_error(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
) -> Callable:
    """Decorator for API calls with automatic retry using tenacity.

    Retries on:
    - TimeoutError
    - ConnectionError
    - Rate limit errors (detected in error message)

    Args:
        max_attempts: Maximum retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay between retries

    Returns:
        Decorator function

    Example:
        @retry_on_api_error(max_attempts=3)
        def call_openai_api():
            ...
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=initial_delay, max=max_delay),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=_log_retry,
        reraise=True,
    )


def retry_on_network_error(
    max_attempts: int = 5,
    initial_delay: float = 2.0,
    max_delay: float = 30.0,
) -> Callable:
    """Decorator for network operations with aggressive retry using tenacity.

    Retries on:
    - TimeoutError
    - ConnectionError
    - ConnectionRefusedError
    - ConnectionResetError

    Args:
        max_attempts: Maximum retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay between retries

    Returns:
        Decorator function
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=initial_delay, max=max_delay),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=_log_retry,
        reraise=True,
    )


def get_error_severity(exception: Exception) -> ErrorSeverity:
    """Determine if error is fatal, recoverable, or warning.

    Args:
        exception: The exception to categorize

    Returns:
        ErrorSeverity category
    """
    # Check specific error types
    if isinstance(
        exception, (PermissionError, FileNotFoundError, ValueError, TypeError)
    ):
        return ErrorSeverity.FATAL

    if isinstance(exception, RETRYABLE_EXCEPTIONS):
        return ErrorSeverity.RECOVERABLE

    # Check MediaFactory exceptions
    if isinstance(exception, MediaFactoryError):
        severity_str = exception.severity
        if severity_str == ErrorSeverity.FATAL.value:
            return ErrorSeverity.FATAL
        elif severity_str == ErrorSeverity.RECOVERABLE.value:
            return ErrorSeverity.RECOVERABLE
        elif severity_str == ErrorSeverity.WARNING.value:
            return ErrorSeverity.WARNING

    # Check for HTTP/API errors (common in LLM backends)
    error_str = str(exception).lower()

    # Auth errors are fatal
    if any(
        kw in error_str
        for kw in ["unauthorized", "authentication", "invalid api key", "401"]
    ):
        return ErrorSeverity.FATAL

    # Rate limit and connection errors are recoverable
    if any(
        kw in error_str
        for kw in ["rate limit", "429", "too many requests", "timeout", "connection"]
    ):
        return ErrorSeverity.RECOVERABLE

    # Server errors may be recoverable
    if any(kw in error_str for kw in ["500", "502", "503", "504"]):
        return ErrorSeverity.RECOVERABLE

    # Default to fatal for unknown errors
    return ErrorSeverity.FATAL


def is_retryable_error(exception: Exception) -> bool:
    """Check if an exception is retryable.

    Args:
        exception: The exception to check

    Returns:
        True if the error is retryable
    """
    return get_error_severity(exception) == ErrorSeverity.RECOVERABLE


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

    def get_severity(self) -> str:
        """获取错误严重程度。"""
        return self.severity

    def is_retryable(self) -> bool:
        """检查错误是否可重试。"""
        return self.severity in (
            ErrorSeverity.RECOVERABLE.value,
            ErrorSeverity.WARNING.value,
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式，便于序列化。"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "context": self.context,
            "severity": self.severity,
            "is_retryable": self.is_retryable(),
        }


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
    # Retry mechanism (tenacity-based)
    "RetryConfig",
    "RETRYABLE_EXCEPTIONS",
    "get_error_severity",
    "is_retryable_error",
    "retry_on_api_error",
    "retry_on_network_error",
    # Base exception
    "MediaFactoryError",
    # Core exceptions (3 types)
    "ProcessingError",
    "ConfigurationError",
    "OperationCancelledError",
]
