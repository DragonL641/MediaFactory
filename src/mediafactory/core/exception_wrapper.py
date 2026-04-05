"""异常转换工具模块

将标准 Python 异常转换为 MediaFactory 结构化异常。
"""

import traceback
from contextlib import contextmanager
from typing import Any, Optional

from ..exceptions import (
    MediaFactoryError,
    ProcessingError,
    ConfigurationError,
    OperationCancelledError,
    ErrorSeverity,
)


def convert_exception(
    exc: Exception,
    context: Optional[dict[str, Any]] = None,
) -> MediaFactoryError:
    """将 Python 异常转换为 MediaFactory 异常

    Args:
        exc: 原始异常
        context: 上下文信息

    Returns:
        转换后的 MediaFactory 异常
    """
    # 捕获异常堆栈
    tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    ctx = {**(context or {})}

    if tb_str and tb_str.strip():
        ctx["traceback"] = tb_str

    # 提取错误位置信息
    if exc.__traceback__:
        tb_frame = exc.__traceback__
        while tb_frame.tb_next:
            tb_frame = tb_frame.tb_next
        frame = tb_frame.tb_frame
        ctx["error_file"] = frame.f_code.co_filename
        ctx["error_line"] = tb_frame.tb_lineno
        ctx["error_function"] = frame.f_code.co_name

    error_str = str(exc).lower()
    ctx["original_exception"] = type(exc).__name__

    # 认证/配置错误 -> ConfigurationError (FATAL)
    auth_config_keywords = (
        "unauthorized",
        "401",
        "authentication",
        "invalid api key",
        "invalid token",
        "access denied",
        "forbidden",
        "config.toml",
        "configuration",
        "settings file",
        "missing configuration",
        "invalid option",
    )
    if any(kw in error_str for kw in auth_config_keywords):
        return ConfigurationError(
            message=str(exc),
            context=ctx,
        )

    # 可恢复错误 -> ProcessingError (RECOVERABLE)
    recoverable_keywords = (
        "rate limit",
        "429",
        "too many requests",
        "quota exceeded",
        "rate_limited",
        "throttle",
        "network",
        "connection",
        "timeout",
        "dns",
        "socket",
        "host unreachable",
        "network unreachable",
        "cuda",
        "gpu",
        "device",
        "nvidia",
        "cuda_runtime",
        "cuda driver",
        "out of memory",
        "oom",
    )
    if any(kw in error_str for kw in recoverable_keywords):
        return ProcessingError(
            message=str(exc),
            context=ctx,
            severity=ErrorSeverity.RECOVERABLE,
        )

    # 默认使用 ProcessingError
    return ProcessingError(
        message=str(exc),
        context=ctx,
    )


@contextmanager
def wrap_exceptions(
    context: Optional[dict[str, Any]] = None,
    operation: Optional[str] = None,
    reraise_types: Optional[tuple[type[Exception], ...]] = None,
):
    """自动包装异常的上下文管理器

    Args:
        context: 上下文信息
        operation: 操作名称
        reraise_types: 不需要包装直接重新抛出的异常类型

    Example:
        with wrap_exceptions(context={"file": path}, operation="extract"):
            # 处理逻辑
            pass
    """
    ctx = {**(context or {})}
    if operation:
        ctx["operation"] = operation

    try:
        yield
    except KeyboardInterrupt:
        raise OperationCancelledError(
            message="Operation cancelled by user",
            context=ctx,
        )
    except MediaFactoryError:
        raise
    except Exception as e:
        if reraise_types and isinstance(e, reraise_types):
            raise
        wrapped = convert_exception(e, context=ctx)
        raise wrapped from e


__all__ = [
    "convert_exception",
    "wrap_exceptions",
]
