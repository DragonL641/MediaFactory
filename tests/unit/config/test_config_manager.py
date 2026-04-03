"""配置管理器（manager.py）单元测试

覆盖加载默认配置、保存与重载、嵌套更新、验证回滚等功能。
"""

import pytest
from pathlib import Path

from mediafactory.config.manager import AppConfigManager
from mediafactory.config.models import AppConfig, WhisperConfig, LLMApiConfig

pytestmark = [pytest.mark.unit]


# ============================================================================
# 1. 加载默认配置
# ============================================================================


class TestLoadDefaultConfig:
    def test_load_or_create_when_no_file(self, tmp_config_file):
        """配置文件不存在时，应创建默认配置并写入磁盘"""
        assert not tmp_config_file.exists()
        manager = AppConfigManager(config_path=tmp_config_file)
        assert isinstance(manager.config, AppConfig)
        assert tmp_config_file.exists()

    def test_default_values(self, tmp_config_file):
        manager = AppConfigManager(config_path=tmp_config_file)
        cfg = manager.config
        assert cfg.whisper.beam_size == 5
        assert cfg.llm_api.timeout == 30
        assert cfg.app.language == "en"
        assert cfg.model.available_translation_models == []

    def test_config_path_property(self, tmp_config_file):
        manager = AppConfigManager(config_path=tmp_config_file)
        assert manager.config_path == tmp_config_file


# ============================================================================
# 2. 保存与重载 round-trip
# ============================================================================


class TestSaveAndReload:
    def test_save_and_reload_preserves_values(self, tmp_config_file):
        """保存后重载应保持修改后的值"""
        manager = AppConfigManager(config_path=tmp_config_file)
        manager.config.whisper.beam_size = 8
        manager.save()

        # 创建新 manager 实例从同一文件加载
        manager2 = AppConfigManager(config_path=tmp_config_file)
        assert manager2.config.whisper.beam_size == 8

    def test_reload_after_save(self, tmp_config_file):
        """reload() 应重新从磁盘读取"""
        manager = AppConfigManager(config_path=tmp_config_file)
        manager.config.llm_api.timeout = 120
        manager.save()

        # 修改内存值但未保存
        manager.config.llm_api.timeout = 30
        # reload 应恢复为磁盘上的值
        manager.reload()
        assert manager.config.llm_api.timeout == 120


# ============================================================================
# 3. update() 双下划线表示法
# ============================================================================


class TestUpdate:
    def test_update_single_field(self, tmp_config_file):
        manager = AppConfigManager(config_path=tmp_config_file)
        manager.update(whisper__beam_size=7)
        assert manager.config.whisper.beam_size == 7
        # 验证已持久化
        manager2 = AppConfigManager(config_path=tmp_config_file)
        assert manager2.config.whisper.beam_size == 7

    def test_update_multiple_fields(self, tmp_config_file):
        manager = AppConfigManager(config_path=tmp_config_file)
        manager.update(
            whisper__beam_size=3,
            llm_api__timeout=60,
            app__language="zh",
        )
        assert manager.config.whisper.beam_size == 3
        assert manager.config.llm_api.timeout == 60
        assert manager.config.app.language == "zh"

    def test_update_deep_nested_field(self, tmp_config_file):
        """更新 openai_compatible 下的嵌套字段"""
        manager = AppConfigManager(config_path=tmp_config_file)
        manager.update(openai_compatible__current_preset="glm")
        assert manager.config.openai_compatible.current_preset == "glm"

    def test_update_persists_to_disk(self, tmp_config_file):
        """update 应自动保存到磁盘"""
        manager = AppConfigManager(config_path=tmp_config_file)
        manager.update(whisper__beam_size=9)

        # 直接创建新 manager 验证持久化
        manager2 = AppConfigManager(config_path=tmp_config_file)
        assert manager2.config.whisper.beam_size == 9


# ============================================================================
# 4. update() 验证失败回滚
# ============================================================================


class TestUpdateValidationRollback:
    def test_invalid_value_rolls_back(self, tmp_config_file):
        """无效值导致验证失败时，配置应回滚到更新前的状态"""
        manager = AppConfigManager(config_path=tmp_config_file)
        original_beam = manager.config.whisper.beam_size
        assert original_beam == 5

        with pytest.raises(Exception):
            manager.update(whisper__beam_size=999)  # 超出 le=10 约束

        # 原值应保持不变
        assert manager.config.whisper.beam_size == original_beam

    def test_partial_update_failure_rolls_back_all(self, tmp_config_file):
        """如果部分更新失败，所有变更都应回滚"""
        manager = AppConfigManager(config_path=tmp_config_file)
        original_beam = manager.config.whisper.beam_size
        original_timeout = manager.config.llm_api.timeout

        with pytest.raises(Exception):
            manager.update(
                whisper__beam_size=7,      # 这个是合法的
                llm_api__timeout=9999,     # 这个不合法
            )

        # 两个字段都应保持原值
        assert manager.config.whisper.beam_size == original_beam
        assert manager.config.llm_api.timeout == original_timeout


# ============================================================================
# 5. get() / set() 便捷方法
# ============================================================================


class TestGetSetConvenience:
    def test_get_existing_value(self, tmp_config_file):
        manager = AppConfigManager(config_path=tmp_config_file)
        assert manager.get("whisper", "beam_size") == 5

    def test_get_missing_section_returns_default(self, tmp_config_file):
        manager = AppConfigManager(config_path=tmp_config_file)
        assert manager.get("nonexistent", "field", "fallback") == "fallback"

    def test_set_updates_and_persists(self, tmp_config_file):
        manager = AppConfigManager(config_path=tmp_config_file)
        manager.set("whisper", "beam_size", 3)
        assert manager.config.whisper.beam_size == 3
        # 验证持久化
        manager2 = AppConfigManager(config_path=tmp_config_file)
        assert manager2.config.whisper.beam_size == 3


# ============================================================================
# 6. has_available_models()
# ============================================================================


class TestHasAvailableModels:
    def test_false_by_default(self, tmp_config_file):
        manager = AppConfigManager(config_path=tmp_config_file)
        assert manager.has_available_models() is False

    def test_true_after_update(self, tmp_config_file):
        manager = AppConfigManager(config_path=tmp_config_file)
        manager.update(model__available_translation_models=["facebook/m2m100_1.2B"])
        assert manager.has_available_models() is True
