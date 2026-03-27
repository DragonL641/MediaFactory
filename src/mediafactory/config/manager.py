"""简化的配置管理器

提供：
- TOML 文件读写
- 嵌套配置更新（双下划线表示法）
- 显式重载配置

对于桌面应用，使用直接属性访问，无需复杂的观察者模式或自动文件监视。
配置仅在显式调用 reload() 时从磁盘重新加载。
"""

import copy
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import tomli
import tomli_w

from .defaults import get_config_path, CONFIG_FILE_BACKUP_SUFFIX
from .models import AppConfig
from ..constants import BackendConfigMapping


class AppConfigManager:
    """简化的配置管理器

    核心方法：
        manager = get_config_manager()
        config = manager.config
        beam_size = config.whisper.beam_size

        # 直接属性修改
        config.whisper.beam_size = 7
        manager.save()

        # 或使用 update 方法
        manager.update(whisper__beam_size=7)

        # 显式重载
        manager.reload()
    """

    _default_instance: Optional["AppConfigManager"] = None

    def __init__(self, config_path: Optional[Path] = None):
        self._config_path = config_path or get_config_path()
        self._config: Optional[AppConfig] = None
        self._config = self._load_or_create()

    # ==================== 属性 ====================

    @property
    def config(self) -> AppConfig:
        """获取当前配置"""
        return self._config

    @property
    def config_path(self) -> Path:
        """获取配置文件路径"""
        return self._config_path

    # ==================== 核心方法 ====================

    def reload(self) -> None:
        """从磁盘重新加载配置"""
        from ..logging import log_info, log_error

        log_info(f"配置重新加载: {self._config_path}")
        try:
            self._config = self._load()
            log_info("配置重新加载完成")
        except Exception as e:
            log_error(f"配置重新加载失败: {e}")
            raise

    def save(self) -> None:
        """保存当前配置到磁盘"""
        from ..logging import log_info, log_error

        log_info(f"配置保存: {self._config_path}")
        try:
            self._save(self._config)
        except Exception as e:
            log_error(f"配置保存失败: {e}")
            raise

    def update(self, **changes) -> None:
        """更新配置值并保存

        使用双下划线表示法进行嵌套访问。

        Args:
            **changes: 键值对，键使用双下划线表示嵌套访问
                      (例如 whisper__beam_size=7)

        Example:
            manager.update(
                whisper__beam_size=7,
                openai_compatible__api_key="sk-...",
            )
        """
        field_changes = self._apply_updates(self._config, changes)
        self._config.model_validate(self._config.model_dump())
        self._save(self._config)

        # 审计日志：记录配置变更
        if field_changes:
            _log_config_changes(field_changes)

    # ==================== 便捷方法 ====================

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """获取配置值"""
        try:
            section_obj = getattr(self.config, section)
            return getattr(section_obj, key)
        except AttributeError:
            return default

    def set(self, section: str, key: str, value: Any) -> None:
        """设置配置值"""
        self.update(**{f"{section}__{key}": value})

    def get_backend_config(self, backend: str) -> Dict[str, Any]:
        """获取后端配置"""
        return BackendConfigMapping.get_backend_config(self.config, backend)

    def has_available_models(self) -> bool:
        """检查是否有可用的翻译模型"""
        return self.config.has_available_models()

    def sync_models(self) -> None:
        """同步本地模型列表到配置文件

        扫描 models/ 目录，检测已下载的模型并更新配置文件。
        使用嵌套目录结构（如 models/Systran/faster-whisper-large-v3/）。

        调用场景：
            - 应用启动时
            - 模型下载完成后
            - 模型删除后
            - 手动刷新时
        """
        from ..models.model_download import is_model_complete
        from ..models.model_registry import MODEL_REGISTRY, ModelType
        from .defaults import get_app_root_dir

        models_dir = get_app_root_dir() / "models"
        translation_models: list[str] = []
        whisper_models: list[str] = []

        if models_dir.exists():
            # 扫描嵌套目录结构: models/{org}/{model_name}/
            for org_dir in models_dir.iterdir():
                if not org_dir.is_dir():
                    continue
                if org_dir.name.startswith("."):
                    continue

                for model_dir in org_dir.iterdir():
                    if not model_dir.is_dir():
                        continue
                    if model_dir.name.startswith("."):
                        continue

                    huggingface_id = f"{org_dir.name}/{model_dir.name}"

                    if not is_model_complete(huggingface_id):
                        continue

                    info = MODEL_REGISTRY.get(huggingface_id)
                    if info:
                        if info.model_type == ModelType.TRANSLATION:
                            translation_models.append(huggingface_id)
                        elif info.model_type == ModelType.WHISPER:
                            whisper_models.append(huggingface_id)

        self.update(
            model__available_translation_models=translation_models,
            model__whisper_models=whisper_models,
        )

    # ==================== 私有方法 ====================

    def _load_or_create(self) -> AppConfig:
        """加载或创建配置"""
        try:
            return self._load()
        except FileNotFoundError:
            config = AppConfig()
            self._save(config, create_backup=False)
            return config

    def _load(self) -> AppConfig:
        """从 TOML 文件加载配置"""
        if not self._config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self._config_path}")

        with open(self._config_path, "rb") as f:
            toml_data = tomli.load(f)

        return self._toml_to_config(toml_data)

    def _save(self, config: AppConfig, create_backup: bool = True) -> None:
        """保存配置到 TOML 文件"""
        if create_backup and self._config_path.exists():
            backup_path = self._config_path.with_suffix(
                self._config_path.suffix + CONFIG_FILE_BACKUP_SUFFIX
            )
            try:
                shutil.copy2(self._config_path, backup_path)
            except OSError:
                pass

        toml_data = self._config_to_toml(config)
        self._config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self._config_path, "wb") as f:
            tomli_w.dump(toml_data, f)

    def _apply_updates(
        self, config: AppConfig, changes: Dict[str, Any]
    ) -> Dict[str, Tuple[Any, Any]]:
        """应用更新并跟踪变更"""
        field_changes: Dict[str, Tuple[Any, Any]] = {}

        for key, value in changes.items():
            keys = key.split("__")
            obj = config

            for k in keys[:-1]:
                obj = getattr(obj, k)

            final_key = keys[-1]
            field_path = ".".join(keys)
            old_value = getattr(obj, final_key)

            setattr(obj, final_key, value)
            field_changes[field_path] = (old_value, value)

        return field_changes

    def _toml_to_config(self, toml_data: Dict[str, Any]) -> AppConfig:
        """将 TOML 数据转换为 AppConfig"""
        config_data: Dict[str, Any] = {}

        for section_name, section_data in toml_data.items():
            if not isinstance(section_data, dict):
                continue

            if section_name == "model":
                config_data[section_name] = self._parse_model_section(section_data)
            elif section_name == "local_models":
                if "model" not in config_data:
                    config_data["model"] = {}
                self._merge_local_models_section(config_data["model"], section_data)
            else:
                config_data[section_name] = section_data

        return AppConfig(**config_data)

    def _parse_model_section(self, section_data: Dict[str, Any]) -> Dict[str, Any]:
        """解析 model 配置节"""
        result = copy.deepcopy(section_data)

        list_fields = ["available_translation_models", "whisper_models"]
        for field in list_fields:
            if field in result:
                value = result[field]
                if isinstance(value, str):
                    result[field] = [v.strip() for v in value.split(",") if v.strip()]
                elif not isinstance(value, list):
                    result[field] = []

        return result

    def _merge_local_models_section(
        self, model_section: Dict[str, Any], local_models_data: Dict[str, Any]
    ) -> None:
        """合并 local_models 配置节到 model"""
        field_mapping = {
            "translation_models": "available_translation_models",
            "whisper_models": "whisper_models",
        }

        for old_name, new_name in field_mapping.items():
            if old_name in local_models_data:
                value = local_models_data[old_name]
                if isinstance(value, str):
                    model_section[new_name] = [
                        v.strip() for v in value.split(",") if v.strip()
                    ]
                elif isinstance(value, list):
                    model_section[new_name] = value
                else:
                    model_section[new_name] = []

    def _config_to_toml(self, config: AppConfig) -> Dict[str, Any]:
        """将 AppConfig 转换为 TOML 兼容的字典"""
        toml_data = {}

        for section_name in config.model_fields:
            section = getattr(config, section_name)
            if hasattr(section, "model_dump"):
                section_dict = section.model_dump(mode="json", exclude_none=True)
            else:
                section_dict = section

            for key, value in section_dict.items():
                if isinstance(value, Path):
                    section_dict[key] = str(value)

            if section_dict:
                toml_data[section_name] = section_dict

        return toml_data


# ==================== 单例管理 ====================


def get_config_manager(config_path: Optional[Path] = None) -> AppConfigManager:
    """获取全局配置管理器实例"""
    if AppConfigManager._default_instance is None:
        AppConfigManager._default_instance = AppConfigManager(config_path)
    return AppConfigManager._default_instance


def reset_config_manager() -> None:
    """重置全局配置管理器实例（主要用于测试）"""
    AppConfigManager._default_instance = None


# ==================== 审计日志辅助 ====================

# 敏感字段名（日志中需要脱敏）
_SENSITIVE_FIELD_NAMES = {"api_key", "password", "secret", "token"}


def _mask_value(value: Any, field_path: str) -> str:
    """对敏感字段的值进行脱敏

    Args:
        value: 字段值
        field_path: 字段路径（如 openai_compatible.openai.api_key）

    Returns:
        脱敏后的字符串表示
    """
    field_lower = field_path.lower()
    if any(sensitive in field_lower for sensitive in _SENSITIVE_FIELD_NAMES):
        str_val = str(value)
        if len(str_val) > 4:
            return f"****{str_val[-4:]}"
        return "****" if str_val else "(empty)"
    return str(value)


def _log_config_changes(field_changes: Dict[str, Tuple[Any, Any]]) -> None:
    """记录配置变更审计日志

    Args:
        field_changes: 字段变更字典 {field_path: (old_value, new_value)}
    """
    from ..logging import log_info

    if not field_changes:
        return

    log_info(f"配置变更 ({len(field_changes)} 项):")
    for field_path, (old_value, new_value) in field_changes.items():
        old_display = _mask_value(old_value, field_path)
        new_display = _mask_value(new_value, field_path)
        log_info(f"  {field_path}: {old_display} -> {new_display}")
