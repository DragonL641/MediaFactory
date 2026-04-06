"""
API 错误处理

统一错误响应格式，避免内部异常信息泄漏到前端。
"""

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from mediafactory.core.error_utils import sanitize_error  # noqa: F401
from mediafactory.i18n import t

logger = logging.getLogger(__name__)
# API 层使用标准 logging，通过 InterceptHandler 自动重定向到 loguru
# 详见 mediafactory.logging.loguru_logger.setup_logging_intercept


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
