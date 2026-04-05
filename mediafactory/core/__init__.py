"""核心抽象层模块

提供平台基础抽象：CancellationToken、ProgressCallback、ResourceCleanupProtocol。
"""

from .tool import CancellationToken
from .progress_protocol import ProgressCallback, NO_OP_PROGRESS
from .resource_protocol import ResourceCleanupProtocol

__all__ = [
    "CancellationToken",
    "ProgressCallback",
    "NO_OP_PROGRESS",
    "ResourceCleanupProtocol",
]
