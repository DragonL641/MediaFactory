"""
MediaFactory 包主入口点

支持: python -m mediafactory

这将启动 Flet GUI 应用程序。
"""

from mediafactory.gui.flet import launch_gui

if __name__ == "__main__":
    launch_gui()
