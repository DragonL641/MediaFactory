"""MediaFactory LLM 翻译后端包。

此包提供了使用远程大语言模型进行字幕翻译的功能。
使用统一的 OpenAI 兼容后端，支持所有提供 OpenAI 兼容 API 的服务。

支持的服务:
- OpenAI (官方)
- DeepSeek
- 智谱 GLM
- 通义千问
- Moonshot
- 自定义 OpenAI 兼容服务

降级策略:
LLM API 批量翻译 → 纠正 → 分批 → 逐句 → 本地模型 (M2M100-418M)
"""

from typing import Optional

# 导入基础类
from .base import TranslationBackend, TranslationRequest, TranslationResult

# 导入后端实现
from .openai_compatible_backend import OpenAICompatibleBackend

# 导入本地回退
from .local_fallback import LocalModelFallback

__all__ = [
    # 基础类
    "TranslationBackend",
    "TranslationRequest",
    "TranslationResult",
    # 后端类
    "OpenAICompatibleBackend",
    # 本地回退
    "LocalModelFallback",
    # 辅助函数
    "initialize_llm_backend",
]


def initialize_llm_backend(
    config, preset: str = None, skip_availability_check: bool = False
) -> Optional[OpenAICompatibleBackend]:
    """Initialize LLM backend with configuration.

    This is a centralized utility for creating LLM backend instances,
    reducing code duplication across the application.

    Args:
        config: Application Config instance (AppConfig or AppConfigProtocol)
        preset: Optional preset name to use (e.g., 'openai', 'deepseek', 'glm').
                If not specified, uses current_preset from config.
        skip_availability_check: If True, skip the availability check.
                Useful for connection testing where we want to create
                a backend even if it might not be fully configured.

    Returns:
        Initialized OpenAICompatibleBackend instance, or None if initialization fails

    Example:
        >>> backend = initialize_llm_backend(config)
        >>> if backend and backend.is_available:
        ...     result = backend.translate(request)
    """
    from ..constants import BackendConfigMapping
    from ..logging import log_debug, log_error, log_info

    try:
        log_info("正在初始化 LLM 后端")

        # 确定使用哪个预设
        if preset is None:
            preset = config.openai_compatible.current_preset

        # 获取指定预设的配置
        preset_config = config.openai_compatible.get_preset_config(preset)

        # 获取预设的 base_url（如果配置中没有则使用默认值）
        preset_info = BackendConfigMapping.BASE_URL_PRESETS.get(preset, {})
        base_url = preset_config.base_url or preset_info.get("base_url", "")
        model = preset_config.model or (
            preset_info.get("model_examples", [""])[0]
            if preset_info.get("model_examples")
            else ""
        )

        backend_config = {
            "api_key": preset_config.api_key,
            "base_url": base_url,
            "model": model,
        }

        log_debug(
            f"后端配置: preset={preset}, api_key_length={len(backend_config.get('api_key', ''))}, "
            f"base_url={backend_config.get('base_url', '')}, "
            f"model={backend_config.get('model', '')}"
        )

        # Create backend instance directly
        backend = OpenAICompatibleBackend(**backend_config)

        if backend is None:
            log_error("OpenAICompatibleBackend 创建失败")
            return None

        # Check backend availability (skip for connection testing)
        if not skip_availability_check:
            log_debug("检查后端可用性...")
            if not backend.is_available:
                log_error("后端不可用")
                # Try to get more information about why it's not available
                if not getattr(backend, "_api_key", None):
                    log_error("  - API Key 未配置")
                if not getattr(backend, "_base_url", None):
                    log_error("  - Base URL 未配置")
                if getattr(backend, "_client", None) is None:
                    log_error("  - 客户端对象为 None（可能配置错误）")
                return None

        log_info(f"LLM 后端初始化成功 (preset={preset})")
        return backend

    except Exception as e:
        log_error(f"初始化 LLM 后端时发生异常: {e}")
        import traceback

        log_error(f"堆栈跟踪:\n{traceback.format_exc()}")
        return None
