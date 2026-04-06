"""
错误工具函数

提供异常到用户友好消息的转换，供 Service 层和 API 层共同使用。
"""

import logging

from mediafactory.exceptions import MediaFactoryError
from mediafactory.i18n import t

logger = logging.getLogger(__name__)


def sanitize_error(error: Exception) -> str:
    """
    将异常转换为面向用户的友好消息。

    - MediaFactoryError: 使用其 message 字段（已经是用户友好的）
    - 已知标准异常: 返回分类后的通用消息
    - 其他异常: 返回通用错误消息，详细日志记录到 logger
    """
    if isinstance(error, MediaFactoryError):
        return error.message

    if isinstance(error, FileNotFoundError):
        logger.error(f"File not found: {error}")
        return t("error.generic.fileNotFound")
    if isinstance(error, PermissionError):
        logger.error(f"Permission denied: {error}")
        return t("error.generic.permissionDenied")
    if isinstance(
        error, (ConnectionError, ConnectionRefusedError, ConnectionResetError)
    ):
        logger.error(f"Connection error: {error}")
        return t("error.generic.connectionError")
    if isinstance(error, TimeoutError):
        logger.error(f"Timeout: {error}")
        return t("error.generic.timeout")

    # 未知异常: 记录完整信息，返回通用消息
    logger.exception(f"Unhandled error: {error}")
    return t("error.generic.unexpected")
