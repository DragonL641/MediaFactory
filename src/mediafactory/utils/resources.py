"""MediaFactory 的系统资源管理和检查工具。"""

import os
import configparser
from typing import Tuple, Dict, Any

import psutil

from ..logging import log_info, log_warning, log_step, log_success


def get_system_resources() -> Dict[str, Any]:
    """获取当前系统 RAM 和 VRAM 的可用情况。"""
    # Lazy import torch - only needed when checking GPU resources
    try:
        import torch

        gpu_available = torch.cuda.is_available()
    except ImportError:
        gpu_available = False

    resources = {
        "ram_total_gb": psutil.virtual_memory().total / (1024**3),
        "ram_available_gb": psutil.virtual_memory().available / (1024**3),
        "gpu_available": gpu_available,
        "gpu_vram_total_gb": 0.0,
        "gpu_vram_available_gb": 0.0,
        "gpu_name": "None",
    }
    if resources["gpu_available"]:
        try:
            import torch

            resources["gpu_name"] = torch.cuda.get_device_name(0)
            resources["gpu_vram_total_gb"] = torch.cuda.get_device_properties(
                0
            ).total_memory / (1024**3)
            # 使用 torch.cuda.mem_get_info() 获取空闲和总显存
            free, total = torch.cuda.mem_get_info(0)
            resources["gpu_vram_available_gb"] = free / (1024**3)
        except Exception as e:
            log_warning(f"获取详细 GPU 信息失败: {e}")
    return resources


def check_model_suitability(model_name: str, model_type: str) -> Tuple[bool, str]:
    """检查系统是否能够处理所选模型。

    估算需求（MADLAD400 GGUF 量化模型）：
    - MADLAD400-3B Q4K: ~3GB VRAM / ~4GB RAM
    - MADLAD400-7B Q4K: ~5GB VRAM / ~7GB RAM
    - MADLAD400-3B FP16: ~6GB VRAM / ~10GB RAM
    """
    resources = get_system_resources()
    req_vram = 0.0
    req_ram = 0.0
    if "madlad400-7b" in model_name.lower():
        req_vram = 5.0
        req_ram = 7.0
    elif "madlad400-3b-fp16" in model_name.lower():
        req_vram = 6.0
        req_ram = 10.0
    elif "madlad400" in model_name.lower():
        # MADLAD400-3B Q4K 默认值
        req_vram = 3.0
        req_ram = 4.0
    if resources["gpu_available"]:
        if resources["gpu_vram_available_gb"] < req_vram:
            return (
                False,
                f"{model_name} 显存不足。需要 {req_vram}GB，当前可用 {resources['gpu_vram_available_gb']:.2f}GB。系统可能会卡死。",
            )
    else:
        if resources["ram_available_gb"] < req_ram:
            return (
                False,
                f"{model_name} (CPU 模式) 内存不足。需要 {req_ram}GB，当前可用 {resources['ram_available_gb']:.2f}GB。系统可能会卡死。",
            )
    return True, "系统资源充足。"


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
    # utils_dir 是 src/mediafactory/utils，我们需要 src/mediafactory/resources
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
