"""
MediaFactory 包主入口点

支持: python -m mediafactory

这将启动 Flet GUI 应用程序。
"""

import multiprocessing

from mediafactory.gui.flet import launch_gui

if __name__ == "__main__":
    # PyInstaller 冻结支持 - 防止多进程无限重启
    # 跨平台兼容：Windows、macOS、Linux 都安全
    # 在非冻结环境（开发模式）下是无操作
    multiprocessing.freeze_support()
    launch_gui()
