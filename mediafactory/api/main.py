"""
FastAPI 应用入口

提供 HTTP + WebSocket API 供 Electron 前端调用。
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles

from mediafactory.api.daemon_lock import DaemonAlreadyRunning, DaemonLock
from mediafactory.api.routes import config, models, processing, system

# re-export：保持 mediafactory.api.main.get_task_manager 旧导入路径兼容
from mediafactory.api.task_manager import get_task_manager
from mediafactory.api.websocket import manager as ws_manager
from mediafactory._version import get_version
from mediafactory.config import get_app_root_dir

logger = logging.getLogger(__name__)
# API 层使用标准 logging，通过 InterceptHandler 自动重定向到 loguru
# 详见 mediafactory.logging.loguru_logger.setup_logging_intercept


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("FastAPI application starting...")

    # 启动时：初始化 i18n
    from mediafactory.i18n import init_i18n

    init_i18n()

    # 启动时：后台异步同步本地模型列表到配置文件（避免阻塞启动）
    import asyncio
    from mediafactory.config import get_config_manager

    config_manager = get_config_manager()
    loop = asyncio.get_event_loop()

    async def _sync_models_background():
        try:
            await loop.run_in_executor(None, config_manager.sync_models)
            logger.info("Model sync completed on startup")
        except Exception as e:
            logger.warning(f"Model sync failed on startup (non-fatal): {e}")

    asyncio.create_task(_sync_models_background())

    # 启动时：初始化任务管理器，并恢复上次中断的队列（RUNNING→FAILED，QUEUED 保留）
    task_manager = get_task_manager()
    await task_manager.recover()

    yield

    # 关闭时：清理所有任务
    logger.info("FastAPI application shutting down...")
    await task_manager.shutdown()
    await ws_manager.broadcast(
        {"type": "server_shutdown", "message": "Server is shutting down"}
    )


# SPA 客户端路由（BrowserRouter history 模式）——新页面在此追加
_SPA_PATHS = ("/tasks", "/settings")


def _webui_dir() -> Path:
    """Web UI 构建产物目录（vite 输出；缺失时纯 API 模式）。"""
    return get_app_root_dir() / "webui"


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    app = FastAPI(
        title="MediaFactory API",
        description="多媒体处理平台 API",
        version=get_version(),
        lifespan=lifespan,
    )

    # CORS 配置（允许所有来源，本地桌面工具无安全风险）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
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
    app.include_router(system.router, prefix="/api/system", tags=["system"])

    # WebSocket 端点

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

    # ---- Web UI 同源伺服（注册顺序在既有路由之后，不影响 /api、/ws、/health）----
    webui = _webui_dir()
    if webui.is_dir():

        def _make_spa_handler(index_file: Path):
            async def _spa_index() -> FileResponse:
                return FileResponse(index_file)

            return _spa_index

        for spa_path in _SPA_PATHS:
            # 客户端路由显式回 index.html（history 模式 fallback）
            app.add_api_route(
                spa_path,
                _make_spa_handler(webui / "index.html"),
                methods=["GET"],
                include_in_schema=False,
            )

        app.mount("/", StaticFiles(directory=webui, html=True), name="webui")
    else:
        logger.warning(
            f"Web UI directory not found at {webui} — running in API-only mode"
        )

    return app


# 全局应用实例（用于 uvicorn）
_app: Optional[FastAPI] = None


def get_app() -> FastAPI:
    """获取全局应用实例"""
    global _app
    if _app is None:
        _app = create_app()
    return _app


def _daemon_lock_path():
    """实例锁路径：data/daemon.lock（与 tasks.db 同目录）。"""
    return get_app_root_dir() / "data" / "daemon.lock"


def start_server(port: int = 8765):
    """启动 API 服务器（命令行入口点）

    Args:
        port: 服务端口，默认 8765
    """
    import multiprocessing
    import uvicorn

    # PyInstaller 冻结支持
    multiprocessing.freeze_support()

    # 实例锁：任何时刻至多一个 daemon（保证 recover 的「running 行 = 死实例」假设）
    try:
        DaemonLock(_daemon_lock_path()).acquire()
    except DaemonAlreadyRunning as e:
        logger.error(str(e))
        raise SystemExit(1)

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
    logger.info(f"Starting MediaFactory API server on http://127.0.0.1:{port}")
    uvicorn.run(
        "mediafactory.api.main:get_app",
        host="127.0.0.1",
        port=port,
        factory=True,
        log_level="info",
    )
