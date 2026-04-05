"""
MediaFactory 包主入口点

支持: python -m mediafactory [--reload] [--port PORT]

这将启动 FastAPI 服务器（为 Electron 前端提供 API）。
--reload 参数启用开发模式热加载。
--port 参数指定服务端口（默认 8765）。
"""

import argparse
import multiprocessing
import uvicorn

from mediafactory.api.main import get_app


def main():
    """启动 API 服务器"""
    # PyInstaller 冻结支持 - 防止多进程无限重启
    multiprocessing.freeze_support()

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
