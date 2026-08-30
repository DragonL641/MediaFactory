"""
MediaFactory 包主入口点

支持: python -m mediafactory [--reload] [--port PORT]

这将启动 FastAPI 服务器（为 Electron 前端提供 API）。
--reload 参数启用开发模式热加载。
--port 参数指定服务端口（默认 8765）。
"""

import argparse
import multiprocessing
import sys

import uvicorn

from mediafactory.api.daemon_lock import DaemonAlreadyRunning, DaemonLock
from mediafactory.api.main import get_app
from mediafactory.config import get_app_root_dir


def _daemon_lock_path():
    """实例锁路径：data/daemon.lock（与 tasks.db 同目录）。"""
    return get_app_root_dir() / "data" / "daemon.lock"


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
        raise SystemExit(1)

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
        # 生产模式
        uvicorn.run(
            get_app(),
            host="127.0.0.1",
            port=args.port,
            log_level="info",
        )


if __name__ == "__main__":
    main()
