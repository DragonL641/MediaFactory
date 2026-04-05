"""MediaFactory 常量定义模块。

集中管理应用程序中的核心常量，避免魔法数字散落在代码各处。
领域特定常量已移至各自的使用模块中。

设计原则：
- 核心常量：语言映射、文件格式、后端配置
- 领域常量：就近放置在使用它们的模块中
- 单一真相源：配置默认值在 config/defaults.py 中定义
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import AppConfig


# =============================================================================
# 语言代码映射（用于 LLM prompt）
# =============================================================================


LANGUAGE_NAMES = {
    "en": "English (英语)",
    "zh": "Chinese (中文)",
    "ja": "Japanese (日语/日本語)",
    "ko": "Korean (韩语/한국어)",
    "es": "Spanish (西班牙语)",
    "fr": "French (法语)",
    "de": "German (德语)",
    "ru": "Russian (俄语)",
    "it": "Italian (意大利语)",
    "pt": "Portuguese (葡萄牙语)",
    "ar": "Arabic (阿拉伯语)",
    "hi": "Hindi (印地语)",
    "th": "Thai (泰语/ภาษาไทย)",
    "vi": "Vietnamese (越南语)",
    "id": "Indonesian (印尼语)",
    "ms": "Malay (马来语)",
    "nl": "Dutch (荷兰语)",
    "pl": "Polish (波兰语)",
    "tr": "Turkish (土耳其语)",
    "sv": "Swedish (瑞典语)",
    "da": "Danish (丹麦语)",
    "no": "Norwegian (挪威语)",
    "fi": "Finnish (芬兰语)",
    "el": "Greek (希腊语)",
    "he": "Hebrew (希伯来语)",
    "cs": "Czech (捷克语)",
    "ro": "Romanian (罗马尼亚语)",
    "hu": "Hungarian (匈牙利语)",
    "uk": "Ukrainian (乌克兰语)",
    "uk-UA": "Ukrainian (乌克兰语)",
    "zh-CN": "Simplified Chinese (简体中文)",
    "zh-TW": "Traditional Chinese (繁体中文)",
}


# =============================================================================
# 文件相关常量
# =============================================================================


class FileConstants:
    """文件相关常量 - 单一真相源。"""

    MODELS_DIR = "models"  # 模型目录名
    CONFIG_FILE = "config.toml"  # 配置文件名

    # 支持的视频格式（完整列表）
    SUPPORTED_VIDEO_EXTENSIONS = frozenset(
        {
            ".mp4",
            ".avi",
            ".mkv",
            ".mov",
            ".wmv",
            ".flv",
            ".webm",
            ".mpg",
            ".mpeg",
            ".m4v",
            ".3gp",
            ".ogv",
            ".ts",
            ".mts",
        }
    )

    # 支持的音频格式
    SUPPORTED_AUDIO_EXTENSIONS = frozenset(
        {
            ".wav",
            ".mp3",
            ".aac",
            ".m4a",
            ".ogg",
            ".flac",
            ".wma",
            ".opus",
        }
    )

    # 支持的字幕格式
    SUPPORTED_SUBTITLE_EXTENSIONS = frozenset({".srt", ".vtt", ".ass", ".ssa"})

    # 支持的文本格式
    SUPPORTED_TEXT_EXTENSIONS = frozenset({".txt", ".md", ".rtf"})

    # 文件大小限制
    MAX_VIDEO_SIZE_MB = 4096  # 4GB
    MAX_AUDIO_SIZE_MB = 2048  # 2GB
    MAX_SUBTITLE_SIZE_MB = 10  # 10MB


# =============================================================================
# 线程相关常量
# =============================================================================


# 线程等待超时（秒）- 用于音频提取监控线程
THREAD_JOIN_TIMEOUT = 1


# =============================================================================
# LLM 模型 Token 限制元数据
# =============================================================================


class ModelTokenLimits:
    """各 LLM 模型的 max_tokens 限制元数据。

    用于：
    1. UI 显示模型限制提示
    2. 自动调整用户配置的 max_tokens 不超过模型限制
    3. 为未配置 max_tokens 的预设提供默认值
    """

    # 模型前缀 -> 最大输出 tokens 映射
    # 注意：按前缀长度降序排列，确保更具体的匹配优先
    LIMITS: dict[str, int] = {
        # OpenAI
        "gpt-4o-mini": 16384,
        "gpt-4o": 4096,
        "gpt-4-turbo": 4096,
        "gpt-4-32k": 32768,
        "gpt-4": 4096,
        "gpt-3.5-turbo-16k": 16384,
        "gpt-3.5-turbo": 4096,
        # 智谱 GLM (注意：所有 GLM-4 系列输出限制都是 4K)
        "glm-4-flash": 4096,
        "glm-4-plus": 4096,
        "glm-4-air": 4096,
        "glm-4-long": 4096,  # 超长输入，但输出仍 4K
        "glm-4": 4096,
        # DeepSeek
        "deepseek-chat": 4096,
        "deepseek-coder": 4096,
        # 通义千问
        "qwen-turbo": 8192,
        "qwen-plus": 8192,
        "qwen-max": 8192,
        # Moonshot
        "moonshot-v1-8k": 8192,
        "moonshot-v1-32k": 8192,
        "moonshot-v1-128k": 8192,
    }  # 默认限制（未知模型使用保守值）
    DEFAULT_LIMIT = 4096

    # 缓存排序后的前缀，避免每次调用重复排序
    _SORTED_PREFIXES: list[str] = sorted(LIMITS.keys(), key=len, reverse=True)


def get_model_max_tokens(model_name: str) -> int:
    """获取模型的最大输出 token 限制。

    使用前缀匹配，支持带版本后缀的模型名称（如 GLM-4-Flash-250414）。

    Args:
        model_name: 模型名称（不区分大小写）

    Returns:
        模型的最大输出 token 限制
    """
    if not model_name:
        return ModelTokenLimits.DEFAULT_LIMIT

    model_lower = model_name.lower()

    for prefix in ModelTokenLimits._SORTED_PREFIXES:
        if model_lower.startswith(prefix):
            return ModelTokenLimits.LIMITS[prefix]

    return ModelTokenLimits.DEFAULT_LIMIT


# =============================================================================
# LLM 后端配置映射
# =============================================================================


class BackendConfigMapping:
    """LLM 后端配置映射 - 单一配置源。

    统一使用 OpenAI 兼容后端，支持所有提供 OpenAI 兼容 API 的服务。
    用户只需配置 base_url + api_key + model 即可使用。
    """

    # 预设的 base_url 模板
    BASE_URL_PRESETS = {
        "openai": {
            "display_name": "OpenAI (Official)",
            "base_url": "https://api.openai.com/v1",
            "model_examples": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
        },
        "deepseek": {
            "display_name": "DeepSeek",
            "base_url": "https://api.deepseek.com",
            "model_examples": ["deepseek-chat", "deepseek-coder"],
        },
        "glm": {
            "display_name": "GLM (Zhipu)",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "model_examples": ["glm-4-flash", "glm-4-plus", "glm-4-air"],
        },
        "qwen": {
            "display_name": "Qwen (Tongyi)",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model_examples": ["qwen-turbo", "qwen-plus", "qwen-max"],
        },
        "moonshot": {
            "display_name": "Moonshot AI",
            "base_url": "https://api.moonshot.cn/v1",
            "model_examples": ["moonshot-v1-8k", "moonshot-v1-32k"],
        },
        "custom": {
            "display_name": "Custom / Local LLM",
            "base_url": "",
            "model_examples": ["qwen2.5:7b", "llama3.1:8b", "mistral:7b"],
        },
    }

    @classmethod
    def get_preset_by_display_name(cls, display_name: str) -> dict:
        """根据显示名称获取预设配置。"""
        for preset_config in cls.BASE_URL_PRESETS.values():
            if preset_config["display_name"] == display_name:
                return preset_config
        return {}

    @classmethod
    def get_preset_key_by_display_name(cls, display_name: str) -> str:
        """根据显示名称获取预设 key。"""
        for preset_key, preset_config in cls.BASE_URL_PRESETS.items():
            if preset_config["display_name"] == display_name:
                return preset_key
        return "custom"
