"""MediaFactory Unified Logging Module.

Provides a unified logging system for all application components using loguru.

All logging (CLI, batch, LLM, GUI) now goes through a single loguru-based system:
- Log files stored in: logs/LOG-YYYY-MM-DD-HHMM.log (dedicated logs directory)
- Thread-safe with enqueue
- No rotation, retention, or compression (single session log)
- Auto-initialization on first import

Usage:
    from mediafactory.logging import log_info, log_error, log_stage

    # All logging writes to the same unified log file
    # GUI does not display logs - only writes to backend file
"""

# Auto-initialize logging on module import
from .loguru_logger import setup_app_logging

setup_app_logging()

# Core setup functions
from .loguru_logger import (
    get_app_logger,
    get_log_file_path,
    is_initialized,
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
    log_stage,
    log_step,
    log_success,
)

# LLM API specific logging
from .loguru_logger import (
    log_llm_request,
    log_llm_response,
    log_llm_retry,
)

# Processing operation logging
from .loguru_logger import (
    log_processing_start,
    log_processing_end,
    log_language_detection,
)

# Context binding
from .loguru_logger import (
    bind_context,
    log_with_context,
)

# Utility functions
from .loguru_logger import open_log_folder

__all__ = [
    # Core setup
    "setup_app_logging",
    "get_app_logger",
    "get_log_file_path",
    "is_initialized",
    # Simple logging functions
    "log_debug",
    "log_info",
    "log_warning",
    "log_error",
    "log_exception",
    "log_error_with_context",
    # Structured logging
    "log_stage",
    "log_step",
    "log_success",
    # LLM API logging
    "log_llm_request",
    "log_llm_response",
    "log_llm_retry",
    # Processing logging
    "log_processing_start",
    "log_processing_end",
    "log_language_detection",
    # Context binding
    "bind_context",
    "log_with_context",
    # GUI utility
    "open_log_folder",
]
