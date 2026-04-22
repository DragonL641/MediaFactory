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


def get_config_path() -> Path:
    """获取配置文件路径"""
    return get_app_root_dir() / DEFAULT_CONFIG_FILE
