"""MediaFactory Unified Logging Module.

Provides a unified logging system for all application components using loguru.

All logging (service, pipeline, engine, API, LLM) now goes through a single loguru-based system:
- Log files stored in: logs/LOG-YYYY-MM-DD-HHMM.log (dedicated logs directory)
- Thread-safe with enqueue
- Auto-cleanup: retains logs for 30 days or max 20 files (whichever is stricter)
- Auto-initialization on first import
- API 层的标准 logging 通过 InterceptHandler 重定向到 loguru

Usage:
    from mediafactory.logging import log_info, log_error

    # All logging writes to the same unified log file
    # Web UI 不直接写日志；日志仅由 daemon 写入，
    # 进度与状态通过 WebSocket 推送给 Web UI
"""

# Auto-initialization removed - _ensure_logger() handles lazy init
# This prevents multiple log initializations across repeated imports / threads
# Core setup functions
# Simple logging functions (unified for all backend layers)
# Structured logging functions
# LLM API specific logging
# Processing operation logging
from .loguru_logger import (
    get_app_logger,
    get_log_file_path,
    is_initialized,
    log_debug,
    log_error,
    log_error_with_context,
    log_exception,
    log_info,
    log_language_detection,
    log_llm_request,
    log_llm_response,
    log_step,
    log_success,
    log_warning,
    setup_app_logging,
    setup_logging_intercept,
)

__all__ = [
    # Core setup
    "setup_app_logging",
    "get_app_logger",
    "get_log_file_path",
    "is_initialized",
    "setup_logging_intercept",
    # Simple logging functions
    "log_debug",
    "log_info",
    "log_warning",
    "log_error",
    "log_exception",
    "log_error_with_context",
    # Structured logging
    "log_step",
    "log_success",
    # LLM API logging
    "log_llm_request",
    "log_llm_response",
    # Processing logging
    "log_language_detection",
]
