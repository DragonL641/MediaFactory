"""常量定义模块测试

覆盖 BackendConfigMapping 预设配置等核心常量。
"""

import pytest

from mediafactory.constants import BackendConfigMapping

pytestmark = [pytest.mark.unit]


# ============================================================================
# BackendConfigMapping
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
