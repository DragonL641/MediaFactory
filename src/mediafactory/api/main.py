"""
FastAPI 应用入口

提供 HTTP + WebSocket API 供 Electron 前端调用。
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mediafactory.api.routes import config, models, processing
from mediafactory.api.websocket import manager as ws_manager

logger = logging.getLogger(__name__)

# 全局任务管理器
_task_manager: Optional["TaskManager"] = None


def get_task_manager() -> "TaskManager":
    """获取全局任务管理器实例"""
    global _task_manager
    if _task_manager is None:
        from mediafactory.api.task_manager import TaskManager

        _task_manager = TaskManager()
    return _task_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("FastAPI application starting...")

    # 启动时：初始化 i18n
    from mediafactory.i18n import init_i18n
    init_i18n()

    # 启动时：同步本地模型列表到配置文件
    from mediafactory.config import get_config_manager
    config_manager = get_config_manager()
    try:
        config_manager.sync_models()
        logger.info("Model sync completed on startup")
    except Exception as e:
        logger.warning(f"Model sync failed on startup (non-fatal): {e}")

    # 启动时：初始化任务管理器
    task_manager = get_task_manager()
    asyncio.create_task(task_manager.cleanup_loop())

    yield

    # 关闭时：清理所有任务
    logger.info("FastAPI application shutting down...")
    await task_manager.shutdown()
    await ws_manager.broadcast({"type": "server_shutdown", "message": "Server is shutting down"})


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    app = FastAPI(
        title="MediaFactory API",
        description="多媒体处理平台 API",
        version="0.2.1",
        lifespan=lifespan,
    )

    # CORS 配置（仅允许 localhost，用于 Electron）
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1):\d+$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 全局异常处理器（避免内部异常信息泄漏到前端）
    from fastapi.exceptions import RequestValidationError
    from mediafactory.api.error_handler import (
        global_exception_handler,
        validation_exception_handler,
    )

    app.add_exception_handler(Exception, global_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # 注册路由
    app.include_router(processing.router, prefix="/api/processing", tags=["processing"])
    app.include_router(models.router, prefix="/api/models", tags=["models"])
    app.include_router(config.router, prefix="/api/config", tags=["config"])

    # WebSocket 端点
    from fastapi import WebSocket, WebSocketDisconnect

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket 连接入口"""
        await ws_manager.connect(websocket)
        try:
            while True:
                data = await websocket.receive_json()
                await ws_manager.handle_message(websocket, data)
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            ws_manager.disconnect(websocket)

    # 健康检查端点
    @app.get("/health")
    async def health_check():
        """健康检查"""
        return {"status": "healthy"}

    return app


# 全局应用实例（用于 uvicorn）
_app: Optional[FastAPI] = None


def get_app() -> FastAPI:
    """获取全局应用实例"""
    global _app
    if _app is None:
        _app = create_app()
    return _app


def start_server():
    """启动 API 服务器（命令行入口点）"""
    import multiprocessing
    import uvicorn

    # PyInstaller 冻结支持
    multiprocessing.freeze_support()

    # 初始化 loguru 统一日志（确保日志文件已创建）
    from mediafactory.logging import setup_app_logging, setup_logging_intercept
    setup_app_logging()
    setup_logging_intercept()

    # 配置 uvicorn 标准日志（不影响 mediafactory.* 命名空间）
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # 启动服务器
    logger.info("Starting MediaFactory API server on http://127.0.0.1:8765")
    uvicorn.run(
        "mediafactory.api.main:get_app",
        host="127.0.0.1",
        port=8765,
        factory=True,
        log_level="info",
    )
