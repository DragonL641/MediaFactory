"""MediaFactory Unified Logging Module.

Provides a unified logging system for all application components using loguru.

All logging (CLI, batch, LLM, GUI, API) now goes through a single loguru-based system:
- Log files stored in: logs/LOG-YYYY-MM-DD-HHMM.log (dedicated logs directory)
- Thread-safe with enqueue
- Auto-cleanup: retains logs for 30 days or max 20 files (whichever is stricter)
- Auto-initialization on first import

Usage:
    from mediafactory.logging import log_info, log_error

    # All logging writes to the same unified log file
    # GUI does not display logs - only writes to backend file
"""

# Auto-initialization removed - _ensure_logger() handles lazy init
# This prevents multiple log initializations in Flet multiprocessing environment
from .loguru_logger import setup_app_logging

# Core setup functions
from .loguru_logger import (
    get_app_logger,
    get_log_file_path,
    is_initialized,
    setup_logging_intercept,
)

# Simple logging functions (unified for both app and GUI)
from .loguru_logger import (
    log_debug,
    log_info,
    log_warning,
    log_error,
    log_exception,
    log_error_with_context,
)

# Structured logging functions
from .loguru_logger import (
    log_step,
    log_success,
)

# LLM API specific logging
from .loguru_logger import (
    log_llm_request,
    log_llm_response,
)

# Processing operation logging
from .loguru_logger import (
    log_language_detection,
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
