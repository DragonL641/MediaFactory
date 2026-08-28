"""MediaFactory 常量定义模块。

集中管理应用程序中的核心常量，避免魔法数字散落在代码各处。
领域特定常量已移至各自的使用模块中。

设计原则：
- 核心常量：语言映射、线程、后端配置
- 领域常量：就近放置在使用它们的模块中
- 单一真相源：配置默认值在 config/defaults.py 中定义
"""


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


# CJK 语言代码集合
CJK_LANG_CODES = frozenset({"ja", "zh", "ko", "zh-TW", "zh-CN"})
# 中文变体语言代码集合
CHINESE_LANG_CODES = frozenset({"zh", "zh-CN", "zh-TW"})


# =============================================================================
# 线程相关常量
# =============================================================================


# 线程等待超时（秒）- 用于音频提取监控线程
THREAD_JOIN_TIMEOUT = 1


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
