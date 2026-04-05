"""
API 错误处理

统一错误响应格式，避免内部异常信息泄漏到前端。
"""

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from mediafactory.exceptions import MediaFactoryError
from mediafactory.i18n import t

logger = logging.getLogger(__name__)
# API 层使用标准 logging，通过 InterceptHandler 自动重定向到 loguru
# 详见 mediafactory.logging.loguru_logger.setup_logging_intercept


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


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """FastAPI 全局异常处理器"""
    user_message = sanitize_error(exc)
    return JSONResponse(
        status_code=500,
        content={"detail": user_message},
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """请求验证异常处理器"""
    return JSONResponse(
        status_code=422,
        content={"detail": t("error.generic.validationFailed")},
    )
