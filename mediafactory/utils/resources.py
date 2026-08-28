"""MediaFactory 的语言资源工具。"""

import os
import configparser
from typing import Dict

from ..logging import log_warning


def _load_languages() -> Dict[str, str]:
    """从 languages.ini 加载语言映射，如果不存在则使用默认值。"""
    default_map = {
        "auto": "Auto Detect (自动检测)",
        "en": "English (英语)",
        "zh": "Chinese (中文)",
        "ja": "Japanese (日语)",
        "ko": "Korean (韩语)",
        "fr": "French (法语)",
        "de": "German (德语)",
        "es": "Spanish (西班牙语)",
        "ru": "Russian (俄语)",
        "ar": "Arabic (阿拉伯语)",
        "hi": "Hindi (印地语)",
        "it": "Italian (意大利语)",
        "pt": "Portuguese (葡萄牙语)",
        "nl": "Dutch (荷兰语)",
    }

    # 首先尝试从包内的 resources 文件夹加载
    utils_dir = os.path.dirname(os.path.abspath(__file__))
    # utils_dir 是 mediafactory/utils，我们需要 mediafactory/resources
    config_path = os.path.join(os.path.dirname(utils_dir), "resources", "languages.ini")

    # 如果不存在，再尝试从当前工作目录加载（兼容旧位置或用户自定义）
    if not os.path.exists(config_path):
        config_path = os.path.join(os.getcwd(), "languages.ini")
    if os.path.exists(config_path):
        try:
            parser = configparser.ConfigParser()
            parser.read(config_path, encoding="utf-8")
            if "languages" in parser:
                return dict(parser["languages"])
        except Exception as e:
            log_warning(f"加载 languages.ini 失败: {e}")

    return default_map


LANGUAGE_MAP = _load_languages()


def get_language_name(code: str) -> str:
    """将语言代码转换为可读语言名称。

    优先使用 LANGUAGE_MAP（带中文显示名），如果找不到则回退到 LANGUAGE_NAMES（英文名）。
    """
    # 首先尝试带中文显示名的映射
    if code in LANGUAGE_MAP:
        return LANGUAGE_MAP[code]

    # 回退到英文名映射（用于 LLM prompt）
    from ..constants import LANGUAGE_NAMES

    return LANGUAGE_NAMES.get(code, code)
