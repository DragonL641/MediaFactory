"""核心抽象层模块

提供平台基础抽象：CancellationToken、ProgressCallback、ResourceCleanupProtocol、sanitize_error。
"""

from .tool import CancellationToken
from .progress_protocol import ProgressCallback, NO_OP_PROGRESS
from .resource_protocol import ResourceCleanupProtocol
from .error_utils import sanitize_error

__all__ = [
    "CancellationToken",
    "ProgressCallback",
    "NO_OP_PROGRESS",
    "ResourceCleanupProtocol",
    "sanitize_error",
]
