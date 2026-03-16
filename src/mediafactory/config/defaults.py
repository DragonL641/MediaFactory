"""Default configuration constants for MediaFactory.

仅保留路径、枚举等通用常量。
配置默认值已移至 models.py 的 Field 中。
"""

import sys
from enum import Enum
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
DEFAULT_CACHE_PATH = Path("./cache")
DEFAULT_LOG_PATH = Path("./logs")


# ============================================================================
# 模型下载源
# ============================================================================

DEFAULT_DOWNLOAD_SOURCE = "https://hf-mirror.com"  # 默认使用中国镜像
CHINA_MIRROR_SOURCE = "https://hf-mirror.com"
OFFICIAL_SOURCE = "https://huggingface.co"


# ============================================================================
# 枚举类型
# ============================================================================


class Backend(str, Enum):
    """支持的 LLM 后端标识"""

    OPENAI_COMPATIBLE = "openai_compatible"


class Language(str, Enum):
    """常用语言代码"""

    ENGLISH = "en"
    CHINESE = "zh"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    JAPANESE = "ja"
    KOREAN = "ko"
    RUSSIAN = "ru"
    PORTUGUESE = "pt"
    ITALIAN = "it"


# ============================================================================
# 路径工具函数
# ============================================================================


def get_default_config_path() -> Path:
    """获取默认配置文件路径"""
    return Path.cwd() / DEFAULT_CONFIG_FILE


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
        # src/mediafactory/config -> src/mediafactory -> src -> project root
        return Path(__file__).parent.parent.parent.parent.resolve()


def get_config_path() -> Path:
    """获取配置文件路径"""
    return get_app_root_dir() / DEFAULT_CONFIG_FILE
