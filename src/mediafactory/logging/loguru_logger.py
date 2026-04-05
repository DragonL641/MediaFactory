"""Loguru-based Application Logger Module.

Provides unified logging for all application components using loguru.

Key features:
- Simpler configuration (no need for handlers/formatters)
- Better exception handling with traceback
- Thread-safe logging
- Single log file per application run
- Automatic cleanup of old log files (30 days / max 20 files)
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
from loguru import logger as _loguru_logger

# 日志清理配置（默认值，优先从 config.toml 读取）
_LOG_RETENTION_DAYS = 30
_LOG_MAX_FILES = 20
_LOG_FILE_PATTERN = "LOG-*.log"


def _get_logging_config() -> tuple[int, int]:
    """从配置获取日志保留参数，返回 (retention_days, max_files)"""
    try:
        from ..config import get_config
        config = get_config()
        return config.logging.retention_days, config.logging.max_files
    except Exception:
        return _LOG_RETENTION_DAYS, _LOG_MAX_FILES

# Remove default handler
_loguru_logger.remove()


class LoguruAppLogger:
    """Application logger manager using loguru."""

    def __init__(self):
        """Initialize the logger manager."""
        self.log_file: Optional[Path] = None
        self._initialized = False

    def _get_writable_log_dir(self) -> Path:
        """Get a writable log directory with fallbacks.

        In Windows builds, the app root directory may be protected (e.g., Program Files).
        This method tries multiple locations to find a writable directory.
        """
        import tempfile

        candidates = []

        # Primary: app root
        try:
            from ..config import get_app_root_dir
            app_root = get_app_root_dir()
            candidates.append(app_root / "logs")
        except (ImportError, AttributeError):
            pass

        # Fallback 1: user home
        candidates.append(Path.home() / ".mediafactory" / "logs")

        # Fallback 2: temp directory
        candidates.append(Path(tempfile.gettempdir()) / "mediafactory" / "logs")

        # Fallback 3: current working directory
        candidates.append(Path.cwd() / "logs")

        for candidate in candidates:
            try:
                candidate.mkdir(parents=True, exist_ok=True)
                test_file = candidate / ".write_test"
                test_file.touch()
                test_file.unlink()
                return candidate
            except (OSError, PermissionError):
                continue

        # Last resort: return first candidate even if not writable
        return candidates[0] if candidates else Path.cwd() / "logs"

    def setup(
        self,
        name: str = "mediafactory",
        log_file: Optional[Path] = None,
    ) -> None:
        """Setup the application logging system using loguru.

        Args:
            name: Logger name (for compatibility, loguru doesn't use it)
            log_file: Specific log file path (auto-generated if None)

        Note:
            This method is idempotent - calling it multiple times will not
            add duplicate handlers.
        """
        # Prevent duplicate initialization
        if self._initialized:
            return

        if log_file is None:
            # Use fallback log directory finder
            log_dir = self._get_writable_log_dir()
            log_filename = datetime.now().strftime("LOG-%Y-%m-%d-%H%M.log")
            log_file = log_dir / log_filename

        self.log_file = log_file

        file_handler_added = False
        try:
            _loguru_logger.add(
                log_file,
                level="DEBUG",
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
                enqueue=True,  # Thread-safe logging
            )
            file_handler_added = True
        except Exception as e:
            import sys
            # Fallback to stderr if file logging fails
            _loguru_logger.add(
                sys.stderr,
                level="DEBUG",
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
            )
            _loguru_logger.warning(f"Failed to setup file logging at {log_file}: {e}")

        # Log startup info
        _loguru_logger.info("=" * 60)
        _loguru_logger.info("MediaFactory Application Logger Initialized (Loguru)")
        _loguru_logger.info(f"Log file: {log_file}")
        _loguru_logger.info(f"File logging: {'enabled' if file_handler_added else 'disabled (using stderr)'}")
        _loguru_logger.info("=" * 60)

        # 清理过期日志文件
        self._cleanup_old_logs(log_file.parent)

        self._initialized = True

    def get_logger(self):
        """Get the loguru logger instance."""
        return _loguru_logger

    def get_log_file_path(self) -> str:
        """Get the current log file path."""
        return str(self.log_file) if self.log_file else ""

    def is_initialized(self) -> bool:
        """Check if logger has been initialized."""
        return self._initialized

    def _get_log_config(self) -> tuple[int, int]:
        """获取日志清理配置（retention_days, max_files）"""
        try:
            from mediafactory.config import get_config
            config = get_config()
            return config.logging.retention_days, config.logging.max_files
        except Exception:
            return 30, 20

    def _cleanup_old_logs(self, log_dir: Path) -> None:
        """清理过期日志文件

        清理规则（取更严格的）：
        - 保留最近 30 天内的日志文件
        - 最多保留 20 个日志文件（按修改时间排序）
        - 当前会话的日志文件不会被清理
        """
        if not log_dir.exists():
            return

        # 收集所有日志文件，按修改时间倒序（最新的在前）
        log_files = sorted(
            [f for f in log_dir.glob(_LOG_FILE_PATTERN) if f.is_file()],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )

        # 排除当前会话的日志文件
        if self.log_file:
            log_files = [f for f in log_files if f.resolve() != self.log_file.resolve()]

        if not log_files:
            return

        to_delete: set[Path] = set()

        # 规则 1：删除超过保留天数的文件
        retention_days, max_files = self._get_log_config()
        cutoff_time = time.time() - (retention_days * 86400)
        for f in log_files:
            try:
                if f.stat().st_mtime < cutoff_time:
                    to_delete.add(f)
            except OSError:
                pass

        # 规则 2：超过最大文件数时，删除最旧的
        if len(log_files) > max_files:
            for f in log_files[max_files:]:
                to_delete.add(f)

        # 执行删除
        deleted = 0
        for f in to_delete:
            try:
                f.unlink()
                deleted += 1
            except OSError:
                pass

        if deleted > 0:
            _loguru_logger.info(f"Cleaned up {deleted} old log file(s)")


# Global singleton
_loguru_app_logger = LoguruAppLogger()


def setup_app_logging(
    name: str = "mediafactory",
    log_file: Optional[Path] = None,
) -> None:
    """Setup application logging.

    Args:
        name: Logger name (for compatibility)
        log_file: Specific log file path (auto-generated if None)
    """
    _loguru_app_logger.setup(name, log_file)


def get_app_logger():
    """Get the application logger instance (loguru logger)."""
    return _loguru_app_logger.get_logger()


def get_log_file_path() -> str:
    """Get the current log file path."""
    return _loguru_app_logger.get_log_file_path()


def is_initialized() -> bool:
    """Check if app logger has been initialized."""
    return _loguru_app_logger.is_initialized()


def _ensure_logger():
    """Ensure logger is initialized, initializing if necessary."""
    if not is_initialized():
        setup_app_logging()
    return get_app_logger()


# ===== Standard logging 桥接 =====


import logging


class InterceptHandler(logging.Handler):
    """将标准 logging 重定向到 loguru

    用于 API 层（FastAPI + uvicorn）的日志统一。
    只拦截 mediafactory.* 命名空间的日志，不影响 uvicorn 自身日志。
    """

    def emit(self, record: logging.LogRecord) -> None:
        # 获取对应的 loguru 级别
        try:
            level = _loguru_logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 找到调用者（跳过 logging 内部帧）
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        _loguru_logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging_intercept() -> None:
    """注册 InterceptHandler 到 mediafactory.* 命名空间

    将 API 层的 standard logging 重定向到 loguru。
    不影响 uvicorn/starlette 的日志（它们使用自己的命名空间）。
    """
    _ensure_logger()

    mediafactory_logger = logging.getLogger("mediafactory")
    mediafactory_logger.handlers = [InterceptHandler()]
    mediafactory_logger.setLevel(logging.DEBUG)
    mediafactory_logger.propagate = False


# ===== Simple logging functions =====


def log_debug(msg: str, **kwargs) -> None:
    """Log DEBUG level message."""
    _ensure_logger().debug(msg, **kwargs)


def log_info(msg: str, **kwargs) -> None:
    """Log INFO level message."""
    _ensure_logger().info(msg, **kwargs)


def log_warning(msg: str, **kwargs) -> None:
    """Log WARNING level message."""
    _ensure_logger().warning(msg, **kwargs)


def log_error(msg: str, extra: Optional[dict] = None, **kwargs) -> None:
    """Log ERROR level message with optional extra context.

    Args:
        msg: Error message
        extra: Optional dictionary with extra context (will be merged with kwargs)
        **kwargs: Additional keyword arguments passed to loguru
    """
    log_kwargs = {**(extra or {}), **kwargs}
    _ensure_logger().error(msg, **log_kwargs)


def log_exception(msg: str = "") -> None:
    """Log exception with automatic traceback capture.

    Uses loguru's .exception() which automatically includes the current
    exception's traceback with file/line information.

    Args:
        msg: Optional message to prefix the exception
    """
    _ensure_logger().exception(msg)


def log_error_with_context(
    message: str,
    error: Exception,
    context: Optional[dict] = None,
) -> None:
    """Log error with full context using loguru's structured logging.

    This function uses loguru's automatic exception capturing and bind()
    for context, providing cleaner output with automatic traceback and
    file/line information.

    Args:
        message: Main error message
        error: The exception object
        context: Optional dictionary with additional context

    Example output:
        2025-02-08 14:30:15 | ERROR    | Processing failed: File not found
        2025-02-08 14:30:15 | ERROR    | Traceback (most recent call last):
                                      File "/path/to/file.py", line 42, in process_file
                                        raise ProcessingError(...)
                                  mediafactory.exceptions.ProcessingError: File not found
        2025-02-08 14:30:15 | ERROR    | Additional context file_path=/path/to/file.mp4
    """
    _log = _ensure_logger()

    # Log the main error message with exception traceback
    if error.__traceback__:
        # Has traceback - use .exception() for automatic capture
        bound = _log.bind(**(context or {}))
        bound.exception(f"{message}: {error}")
    else:
        # No traceback - use .error() with context
        ctx = context or {}
        ctx_str = ", ".join(f"{k}={v}" for k, v in ctx.items())
        full_msg = f"{message}: {error}"
        if ctx_str:
            full_msg += f" | {ctx_str}"
        _log.error(full_msg)


# ===== Structured logging functions =====


def log_stage(stage_name: str) -> None:
    """Log a processing stage header."""
    _log = _ensure_logger()
    _log.info("=" * 50)
    _log.info(f"STAGE: {stage_name}")
    _log.info("=" * 50)


def log_step(step_msg: str) -> None:
    """Log a processing step."""
    _ensure_logger().info(f"  → {step_msg}")


def log_success(msg: str) -> None:
    """Log a success message."""
    _ensure_logger().info(f"✓ {msg}")


# ===== LLM API specific logging functions =====


def log_llm_request(
    backend: str,
    model: str,
    text_length: int,
    src_lang: Optional[str] = None,
    tgt_lang: Optional[str] = None,
    batch_size: int = 1,
) -> None:
    """Log LLM API request details."""
    _log = _ensure_logger()
    _log.info(f"LLM Request: {backend} / {model}")
    _log.info(f"  Context: src={src_lang}, tgt={tgt_lang}, batch_size={batch_size}")
    _log.info(f"  Input length: {text_length} characters")


def log_llm_response(
    backend: str,
    success: bool,
    output_length: int = 0,
    error: Optional[str] = None,
    retry_count: int = 0,
) -> None:
    """Log LLM API response details."""
    _log = _ensure_logger()
    if success:
        _log.info(f"LLM Response: {backend} - SUCCESS")
        _log.info(f"  Output length: {output_length} characters")
        if retry_count > 0:
            _log.info(f"  Retries: {retry_count}")
    else:
        _log.error(f"LLM Response: {backend} - FAILED")
        _log.error(f"  Error: {error}")
        _log.error(f"  Retries attempted: {retry_count}")


def log_llm_retry(
    backend: str,
    attempt: int,
    max_retries: int,
    error: str,
) -> None:
    """Log LLM API retry attempt."""
    _log = _ensure_logger()
    _log.warning(f"LLM Retry: {backend} - Attempt {attempt}/{max_retries}")
    _log.warning(f"  Error: {error}")


def log_processing_start(
    process_type: str,
    video_path: str,
    context: dict,
) -> None:
    """Log the start of a processing operation."""
    _log = _ensure_logger()
    _log.info("")
    _log.info("=" * 60)
    _log.info(f"START: {process_type}")
    _log.info(f"  Video: {video_path}")
    for key, value in context.items():
        _log.info(f"  {key}: {value}")
    _log.info("=" * 60)


def log_processing_end(
    process_type: str,
    success: bool,
    duration_sec: float,
    output_path: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    """Log the end of a processing operation."""
    _log = _ensure_logger()
    _log.info("")
    _log.info("=" * 60)
    if success:
        _log.info(f"END: {process_type} - SUCCESS")
        _log.info(f"  Duration: {duration_sec:.2f} seconds")
        if output_path:
            _log.info(f"  Output: {output_path}")
    else:
        _log.error(f"END: {process_type} - FAILED")
        _log.error(f"  Duration: {duration_sec:.2f} seconds")
        if error:
            _log.error(f"  Error: {error}")
    _log.info("=" * 60)


def log_language_detection(result: Any, context: str = "") -> None:
    """Log language detection result."""
    from ..utils.resources import LANGUAGE_MAP

    _log = _ensure_logger()
    prefix = f"[{context}] " if context else ""

    _log.info(f"{prefix}Language Detection Result:")
    _log.info(
        f"  Primary Language: {result.primary_language_name} ({result.primary_language})"
    )
    _log.info(f"  Confidence: {result.confidence:.2%}")
    _log.info(f"  Detection Method: {result.detection_method}")
    _log.info(f"  Mixed Language: {'Yes' if result.is_mixed else 'No'}")

    if result.language_distribution:
        _log.info(f"  Language Distribution:")
        for lang_code, percentage in sorted(
            result.language_distribution.items(), key=lambda x: x[1], reverse=True
        ):
            lang_name = LANGUAGE_MAP.get(lang_code, lang_code)
            _log.info(f"    - {lang_name} ({lang_code}): {percentage:.1f}%")

    if result.is_mixed:
        _log.warning(
            f"{prefix}Mixed language content detected, translation quality may be affected"
        )


# ===== Bind/context support for structured logging =====


def bind_context(**kwargs) -> Any:
    """Bind context to logger for structured logging."""
    return _ensure_logger().bind(**kwargs)


def log_with_context(level: str, msg: str, **kwargs) -> None:
    """Log with additional context using loguru's bind."""
    log_func = getattr(_ensure_logger(), level.lower(), None)
    if log_func:
        log_func.bind(**kwargs)(msg)
    else:
        _ensure_logger().info(msg)


# ===== Utility functions =====


def open_log_folder() -> None:
    """Open the folder containing the log file.

    Opens the folder in the system file manager (Finder on macOS,
    Explorer on Windows).
    """
    import os
    import subprocess
    import platform

    log_path = _loguru_app_logger.get_log_file_path()
    if not log_path:
        return

    folder = os.path.dirname(log_path)
    if not os.path.exists(folder):
        return

    if platform.system() == "Windows":
        os.startfile(folder)
    else:
        subprocess.run(["open", folder])
