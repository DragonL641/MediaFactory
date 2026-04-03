"""常量定义模块测试

覆盖 get_model_max_tokens、BackendConfigMapping 等核心常量。
"""

import pytest

from mediafactory.constants import (
    BackendConfigMapping,
    ModelTokenLimits,
    get_model_max_tokens,
)

pytestmark = [pytest.mark.unit]


# ============================================================================
# 1. get_model_max_tokens() - 已知模型
# ============================================================================


class TestGetModelMaxTokensKnownModels:
    """已知模型名应返回正确的 token 限制"""

    def test_gpt4o_mini(self):
        assert get_model_max_tokens("gpt-4o-mini") == 16384

    def test_gpt4o(self):
        assert get_model_max_tokens("gpt-4o") == 4096

    def test_gpt4(self):
        assert get_model_max_tokens("gpt-4") == 4096

    def test_gpt4_turbo(self):
        assert get_model_max_tokens("gpt-4-turbo") == 4096

    def test_gpt4_32k(self):
        assert get_model_max_tokens("gpt-4-32k") == 32768

    def test_gpt35_turbo(self):
        assert get_model_max_tokens("gpt-3.5-turbo") == 4096

    def test_gpt35_turbo_16k(self):
        assert get_model_max_tokens("gpt-3.5-turbo-16k") == 16384

    def test_deepseek_chat(self):
        assert get_model_max_tokens("deepseek-chat") == 4096

    def test_glm4_flash(self):
        assert get_model_max_tokens("glm-4-flash") == 4096

    def test_qwen_turbo(self):
        assert get_model_max_tokens("qwen-turbo") == 8192

    def test_moonshot_v1_8k(self):
        assert get_model_max_tokens("moonshot-v1-8k") == 8192


# ============================================================================
# 2. get_model_max_tokens() - 前缀匹配
# ============================================================================


class TestGetModelMaxTokensPrefixMatching:
    """带版本后缀的模型名应通过前缀匹配返回正确值"""

    def test_gpt4o_mini_with_suffix(self):
        assert get_model_max_tokens("gpt-4o-mini-2024-07-18") == 16384

    def test_gpt4o_with_suffix(self):
        assert get_model_max_tokens("gpt-4o-2024-08-06") == 4096

    def test_glm4_flash_with_date_suffix(self):
        """GLM-4-Flash-250414 应匹配 glm-4-flash 前缀"""
        assert get_model_max_tokens("glm-4-flash-250414") == 4096

    def test_case_insensitive(self):
        assert get_model_max_tokens("GPT-4O-MINI") == 16384

    def test_case_insensitive_glm(self):
        assert get_model_max_tokens("GLM-4-Flash") == 4096

    def test_longer_prefix_takes_priority(self):
        """gpt-4o-mini (11 chars) 应优先于 gpt-4o (6 chars)"""
        mini_result = get_model_max_tokens("gpt-4o-mini")
        regular_result = get_model_max_tokens("gpt-4o")
        assert mini_result == 16384
        assert regular_result == 4096
        assert mini_result != regular_result


# ============================================================================
# 3. get_model_max_tokens() - 未知模型与边界
# ============================================================================


class TestGetModelMaxTokensUnknown:
    """未知模型和边界情况"""

    def test_unknown_model_returns_default(self):
        assert get_model_max_tokens("unknown-model-xyz") == ModelTokenLimits.DEFAULT_LIMIT

    def test_empty_string_returns_default(self):
        assert get_model_max_tokens("") == ModelTokenLimits.DEFAULT_LIMIT

    def test_default_value_is_4096(self):
        assert ModelTokenLimits.DEFAULT_LIMIT == 4096


# ============================================================================
# 4. BackendConfigMapping
# ============================================================================


class TestBackendConfigMapping:
    """BackendConfigMapping 预设配置测试"""

    def test_has_openai_preset(self):
        assert "openai" in BackendConfigMapping.BASE_URL_PRESETS

    def test_has_deepseek_preset(self):
        assert "deepseek" in BackendConfigMapping.BASE_URL_PRESETS

    def test_has_glm_preset(self):
        assert "glm" in BackendConfigMapping.BASE_URL_PRESETS

    def test_has_qwen_preset(self):
        assert "qwen" in BackendConfigMapping.BASE_URL_PRESETS

    def test_has_moonshot_preset(self):
        assert "moonshot" in BackendConfigMapping.BASE_URL_PRESETS

    def test_has_custom_preset(self):
        assert "custom" in BackendConfigMapping.BASE_URL_PRESETS

    def test_preset_has_required_fields(self):
        for key, preset in BackendConfigMapping.BASE_URL_PRESETS.items():
            assert "display_name" in preset, f"Preset '{key}' missing display_name"
            assert "base_url" in preset, f"Preset '{key}' missing base_url"
            assert "model_examples" in preset, f"Preset '{key}' missing model_examples"

    def test_openai_preset_values(self):
        preset = BackendConfigMapping.BASE_URL_PRESETS["openai"]
        assert preset["display_name"] == "OpenAI (Official)"
        assert preset["base_url"] == "https://api.openai.com/v1"
        assert "gpt-4o" in preset["model_examples"]

    def test_deepseek_preset_values(self):
        preset = BackendConfigMapping.BASE_URL_PRESETS["deepseek"]
        assert preset["display_name"] == "DeepSeek"
        assert preset["base_url"] == "https://api.deepseek.com"

    def test_get_preset_by_display_name(self):
        result = BackendConfigMapping.get_preset_by_display_name("OpenAI (Official)")
        assert result["base_url"] == "https://api.openai.com/v1"

    def test_get_preset_by_unknown_display_name(self):
        result = BackendConfigMapping.get_preset_by_display_name("Unknown Service")
        assert result == {}

    def test_get_preset_key_by_display_name(self):
        key = BackendConfigMapping.get_preset_key_by_display_name("DeepSeek")
        assert key == "deepseek"

    def test_get_preset_key_by_unknown_returns_custom(self):
        key = BackendConfigMapping.get_preset_key_by_display_name("NonExistent")
        assert key == "custom"
