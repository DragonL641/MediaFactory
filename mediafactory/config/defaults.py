"""Default configuration constants for MediaFactory.

仅保留路径等通用常量。
配置默认值已移至 models.py 的 Field 中。
"""

import sys
from pathlib import Path


# ============================================================================
# 配置文件
# ============================================================================

DEFAULT_CONFIG_FILE = "config.toml"
CONFIG_FILE_BACKUP_SUFFIX = ".backup"


# ============================================================================
# 默认路径
# ============================================================================

DEFAULT_MODELS_PATH = Path("./models")


# ============================================================================
# 路径工具函数
# ============================================================================


def get_models_path() -> Path:
    """获取默认模型目录路径"""
    return DEFAULT_MODELS_PATH


def get_app_root_dir() -> Path:
    """获取应用根目录

    在 PyInstaller 打包环境中返回可执行文件所在目录。
    在开发环境中返回项目根目录。
    """
    if getattr(sys, "frozen", False):
        # PyInstaller 打包环境
        if hasattr(sys, "_MEIPASS"):
            # --onefile 模式
            return Path(sys.executable).parent
        else:
            # --onedir 模式
            return Path(sys.executable).parent
    else:
        # 开发环境
        # mediafactory/config -> mediafactory -> project root
        return Path(__file__).parent.parent.parent.resolve()


def get_data_root_dir() -> Path:
    """获取可变数据根目录（data/、config.toml、logs/、models/ 的父目录）

    开发环境与 get_app_root_dir 相同（项目根）。
    PyInstaller 打包环境返回平台用户数据目录——安装目录（.app/Resources、
    Program Files）可能只读且升级会覆盖，可变数据不能放在那里。
    """
    if getattr(sys, "frozen", False):
        import os

        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "MediaFactory"
        if sys.platform == "win32":
            appdata = os.environ.get("APPDATA")
            if appdata:
                return Path(appdata) / "MediaFactory"
            return Path.home() / "AppData" / "Roaming" / "MediaFactory"
        return Path.home() / ".mediafactory"
    return get_app_root_dir()


def get_config_path() -> Path:
    """获取配置文件路径（config.toml 为可变数据，frozen 下落数据根）"""
    return get_data_root_dir() / DEFAULT_CONFIG_FILE
