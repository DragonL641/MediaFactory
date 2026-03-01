"""
MediaFactory 配置系统

基于 Pydantic v2 的类型安全配置，使用 TOML 存储。

## 快速开始

```python
from mediafactory.config import get_config, save_config

# 获取配置
config = get_config()

# 访问配置值
beam_size = config.whisper.beam_size
api_key = config.openai_compatible.get_preset_config(
    config.openai_compatible.current_preset
).api_key

# 推荐方式：直接属性访问
config.whisper.beam_size = 7
save_config()

# 或使用 update_config（支持嵌套）
from mediafactory.config import update_config
update_config(whisper__beam_size=7)
```

## 配置结构

- `whisper`: Whisper 语音识别设置
- `model`: 模型存储和发现设置
- `openai_compatible`: 统一的 OpenAI 兼容 API 配置
- `llm_api`: LLM API 设置
"""

# 核心模型
from .models import (
    AppConfig,
    OpenAICompatibleConfig,
    LLMApiConfig,
    ModelConfig,
    WhisperConfig,
    PresetServiceConfig,
)

# 管理器
from .manager import (
    AppConfigManager,
    get_config_manager,
    reset_config_manager,
)

# 默认值
from . import defaults
from .defaults import get_app_root_dir, get_config_path, get_models_path

__all__ = [
    # 主 API
    "get_config_manager",
    "get_config",
    "reset_config_manager",
    "AppConfigManager",
    # 配置模型
    "AppConfig",
    "WhisperConfig",
    "ModelConfig",
    "OpenAICompatibleConfig",
    "PresetServiceConfig",
    "LLMApiConfig",
    # 默认值
    "defaults",
    "get_app_root_dir",
    "get_config_path",
    "get_models_path",
    # 便捷函数
    "reload_config",
    "save_config",
    "update_config",
]


def get_config() -> AppConfig:
    """获取当前配置"""
    return get_config_manager().config


def reload_config() -> None:
    """从磁盘重新加载配置"""
    get_config_manager().reload()


def save_config() -> None:
    """保存当前配置到磁盘"""
    get_config_manager().save()


def update_config(**changes) -> None:
    """
    更新配置值并保存

    Args:
        **changes: 键值对，使用双下划线表示嵌套访问
                  (例如 whisper__beam_size=7)
    """
    get_config_manager().update(**changes)
