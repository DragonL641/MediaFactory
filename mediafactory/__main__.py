"""
MediaFactory 包主入口点

支持: python -m mediafactory [--reload] [--port PORT]

这将启动 FastAPI daemon（提供 API 并同源伺服 Web UI）。
--reload 参数启用开发模式热加载。
--port 参数指定服务端口（默认 8765）。
"""

import argparse
import multiprocessing
import sys

import uvicorn

from mediafactory.api.daemon_lock import DaemonAlreadyRunning, DaemonLock
from mediafactory.api.main import get_app
from mediafactory.config import get_data_root_dir


def _daemon_lock_path():
    """实例锁路径：data/daemon.lock（与 tasks.db 同目录）。"""
    return get_data_root_dir() / "data" / "daemon.lock"


def main():
    """启动 API 服务器"""
    # PyInstaller 冻结支持 - 防止多进程无限重启
    multiprocessing.freeze_support()

    # 实例锁：任何时刻至多一个 daemon（保证 recover 的「running 行 = 死实例」假设）
    try:
        _lock = DaemonLock(_daemon_lock_path())
        _lock.acquire()
    except DaemonAlreadyRunning as e:
        print(f"ERROR: {e}", file=sys.stderr)
        # 42 = 实例锁让位特征码，桌面壳据此区分双启动让位与真崩溃
        raise SystemExit(42)

    # 初始化 loguru 统一日志（与 api.main.start_server 一致——本入口是
    # `python -m mediafactory` 与 PyInstaller frozen 的实际路径，缺此日志不落盘）
    from mediafactory.logging import setup_app_logging, setup_logging_intercept

    setup_app_logging()
    setup_logging_intercept()

    parser = argparse.ArgumentParser(description="MediaFactory API Server")
    parser.add_argument("--reload", action="store_true", help="启用开发模式热加载")
    parser.add_argument("--port", type=int, default=8765, help="服务端口")
    args, _ = parser.parse_known_args()

    # PyInstaller 冻结支持 - 防止多进程无限重启
    multiprocessing.freeze_support()

    if args.reload:
        # 开发模式：热加载，监听 mediafactory 目录
        uvicorn.run(
            "mediafactory.api.main:get_app",
            host="127.0.0.1",
            port=args.port,
            factory=True,
            reload=True,
            reload_dirs=["mediafactory"],
            log_level="info",
        )
    else:
        # 生产模式（手动构造 Server 以支持 /api/system/shutdown 优雅停机）
        from mediafactory.api.server_ref import set_server

        server = uvicorn.Server(
            uvicorn.Config(
                get_app(),
                host="127.0.0.1",
                port=args.port,
                log_level="info",
            )
        )
        set_server(server)
        server.run()


if __name__ == "__main__":
    main()
