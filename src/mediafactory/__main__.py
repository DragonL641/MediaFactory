"""
MediaFactory 包主入口点

支持: python -m mediafactory [--reload]

这将启动 FastAPI 服务器（为 Electron 前端提供 API）。
--reload 参数启用开发模式热加载。
"""

import argparse
import multiprocessing
import uvicorn

from mediafactory.api.main import app


def main():
    """启动 API 服务器"""
    parser = argparse.ArgumentParser(description="MediaFactory API Server")
    parser.add_argument("--reload", action="store_true", help="启用开发模式热加载")
    args = parser.parse_args()

    # PyInstaller 冻结支持 - 防止多进程无限重启
    multiprocessing.freeze_support()

    if args.reload:
        # 开发模式：热加载，监听 src/mediafactory 目录
        uvicorn.run(
            "mediafactory.api.main:get_app",
            host="127.0.0.1",
            port=8765,
            factory=True,
            reload=True,
            reload_dirs=["src/mediafactory"],
            log_level="info",
        )
    else:
        # 生产模式
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8765,
            log_level="info",
        )


if __name__ == "__main__":
    main()
