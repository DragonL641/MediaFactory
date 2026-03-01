"""Flet GUI 资源路径工具"""

import sys
from pathlib import Path
import platform


def get_icon_path() -> Path | None:
    """获取应用图标文件路径。

    支持开发环境和 PyInstaller 打包环境。

    Returns:
        图标文件路径，如果文件不存在则返回 None
    """
    # 获取资源目录基础路径
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # PyInstaller 打包环境
        resources_dir = Path(sys._MEIPASS) / "mediafactory" / "resources"
    else:
        # 开发环境
        # gui/flet/resources.py -> src/mediafactory/resources
        resources_dir = Path(__file__).parent.parent.parent / "resources"

    # 根据平台选择图标文件
    system = platform.system()
    if system == "Darwin":  # macOS
        icon_file = "icon.icns"
    elif system == "Windows":  # Windows
        icon_file = "icon.ico"
    else:  # Linux
        icon_file = "icon.png"

    icon_path = resources_dir / icon_file
    return icon_path if icon_path.exists() else None
