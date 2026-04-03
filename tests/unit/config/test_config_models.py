"""配置模型（models.py）单元测试

覆盖各配置模型的默认值、字段约束、预设配置和 TOML 序列化。
"""

import pytest
from pathlib import Path

from mediafactory.config.models import (
    AppConfig,
    AppSettingsConfig,
    FFmpegConfig,
    LLMApiConfig,
    LoggingConfig,
    ModelConfig,
    OpenAICompatibleConfig,
    PresetServiceConfig,
    WhisperConfig,
)

pytestmark = [pytest.mark.unit]


# ============================================================================
# 1. WhisperConfig 默认值与约束
# ============================================================================


class TestWhisperConfig:
    def test_defaults(self):
        cfg = WhisperConfig()
        assert cfg.beam_size == 5
        assert cfg.no_speech_threshold == 0.1
        assert cfg.condition_on_previous_text is False
        assert cfg.word_timestamps is True
        assert cfg.vad_filter is True
        assert cfg.vad_threshold == 0.35
        assert cfg.vad_min_speech_duration_ms == 250
        assert cfg.vad_min_silence_duration_ms == 500

    def test_beam_size_constraint_min(self):
        """beam_size 不能小于 1"""
        with pytest.raises(Exception):
            WhisperConfig(beam_size=0)

    def test_beam_size_constraint_max(self):
        """beam_size 不能大于 10"""
        with pytest.raises(Exception):
            WhisperConfig(beam_size=11)

    def test_beam_size_valid_boundary(self):
        cfg = WhisperConfig(beam_size=1)
        assert cfg.beam_size == 1
        cfg = WhisperConfig(beam_size=10)
        assert cfg.beam_size == 10

    def test_no_speech_threshold_range(self):
        with pytest.raises(Exception):
            WhisperConfig(no_speech_threshold=-0.1)
        with pytest.raises(Exception):
            WhisperConfig(no_speech_threshold=1.1)

    def test_vad_threshold_range(self):
        with pytest.raises(Exception):
            WhisperConfig(vad_threshold=-0.01)
        with pytest.raises(Exception):
            WhisperConfig(vad_threshold=1.01)

    def test_vad_min_speech_duration_ms_range(self):
        with pytest.raises(Exception):
            WhisperConfig(vad_min_speech_duration_ms=-1)
        with pytest.raises(Exception):
            WhisperConfig(vad_min_speech_duration_ms=10001)


# ============================================================================
# 2. ModelConfig 默认值
# ============================================================================


class TestModelConfig:
    def test_defaults(self):
        cfg = ModelConfig()
        assert cfg.local_model_path == Path("./models")
        assert cfg.download_source == "https://hf-mirror.com"
        assert cfg.download_timeout == 30
        assert cfg.available_translation_models == []
        assert cfg.whisper_models == []

    def test_download_timeout_constraint(self):
        with pytest.raises(Exception):
            ModelConfig(download_timeout=5)
        with pytest.raises(Exception):
            ModelConfig(download_timeout=601)

    def test_download_timeout_valid_boundary(self):
        cfg = ModelConfig(download_timeout=10)
        assert cfg.download_timeout == 10
        cfg = ModelConfig(download_timeout=600)
        assert cfg.download_timeout == 600


# ============================================================================
# 3. PresetServiceConfig 和 OpenAICompatibleConfig
# ============================================================================


class TestPresetServiceConfig:
    def test_defaults(self):
        cfg = PresetServiceConfig()
        assert cfg.api_key == ""
        assert cfg.base_url == ""
        assert cfg.model == ""
        assert cfg.connection_available is False


class TestOpenAICompatibleConfig:
    def test_defaults(self):
        cfg = OpenAICompatibleConfig()
        assert cfg.current_preset == "openai"
        # 各预设都有默认配置
        assert isinstance(cfg.openai, PresetServiceConfig)
        assert isinstance(cfg.deepseek, PresetServiceConfig)
        assert isinstance(cfg.glm, PresetServiceConfig)
        assert isinstance(cfg.qwen, PresetServiceConfig)
        assert isinstance(cfg.moonshot, PresetServiceConfig)
        assert isinstance(cfg.custom, PresetServiceConfig)

    def test_get_preset_config_valid(self):
        cfg = OpenAICompatibleConfig()
        for preset in ["openai", "deepseek", "glm", "qwen", "moonshot", "custom"]:
            result = cfg.get_preset_config(preset)
            assert isinstance(result, PresetServiceConfig)

    def test_get_preset_config_invalid(self):
        cfg = OpenAICompatibleConfig()
        with pytest.raises(ValueError, match="Unknown preset"):
            cfg.get_preset_config("nonexistent")

    def test_preset_config_can_be_customized(self):
        cfg = OpenAICompatibleConfig(
            openai=PresetServiceConfig(api_key="sk-test", base_url="https://api.openai.com/v1", model="gpt-4o")
        )
        assert cfg.openai.api_key == "sk-test"
        assert cfg.openai.base_url == "https://api.openai.com/v1"
        assert cfg.openai.model == "gpt-4o"


# ============================================================================
# 4. LLMApiConfig 默认值与约束
# ============================================================================


class TestLLMApiConfig:
    def test_defaults(self):
        cfg = LLMApiConfig()
        assert cfg.timeout == 30
        assert cfg.max_retries == 3
        assert cfg.batch_size == 40
        assert cfg.split_threshold == 10
        assert cfg.temperature == 0.3

    def test_timeout_constraint(self):
        with pytest.raises(Exception):
            LLMApiConfig(timeout=0)
        with pytest.raises(Exception):
            LLMApiConfig(timeout=301)

    def test_max_retries_constraint(self):
        with pytest.raises(Exception):
            LLMApiConfig(max_retries=-1)
        with pytest.raises(Exception):
            LLMApiConfig(max_retries=11)

    def test_batch_size_constraint(self):
        with pytest.raises(Exception):
            LLMApiConfig(batch_size=0)
        with pytest.raises(Exception):
            LLMApiConfig(batch_size=201)

    def test_temperature_constraint(self):
        with pytest.raises(Exception):
            LLMApiConfig(temperature=-0.01)
        with pytest.raises(Exception):
            LLMApiConfig(temperature=2.01)


# ============================================================================
# 5. FFmpegConfig 默认值与约束
# ============================================================================


class TestFFmpegConfig:
    def test_defaults(self):
        cfg = FFmpegConfig()
        assert cfg.soft_subtitle_timeout == 300
        assert cfg.hard_subtitle_timeout == 1800
        assert cfg.multi_subtitle_timeout == 300

    def test_soft_subtitle_timeout_constraint(self):
        with pytest.raises(Exception):
            FFmpegConfig(soft_subtitle_timeout=59)
        with pytest.raises(Exception):
            FFmpegConfig(soft_subtitle_timeout=3601)


# ============================================================================
# 6. LoggingConfig 默认值与约束
# ============================================================================


class TestLoggingConfig:
    def test_defaults(self):
        cfg = LoggingConfig()
        assert cfg.retention_days == 30
        assert cfg.max_files == 20

    def test_retention_days_constraint(self):
        with pytest.raises(Exception):
            LoggingConfig(retention_days=0)
        with pytest.raises(Exception):
            LoggingConfig(retention_days=366)

    def test_max_files_constraint(self):
        with pytest.raises(Exception):
            LoggingConfig(max_files=0)
        with pytest.raises(Exception):
            LoggingConfig(max_files=101)


# ============================================================================
# 7. AppConfig 默认值与 to_toml_dict
# ============================================================================


class TestAppConfig:
    def test_defaults(self):
        cfg = AppConfig()
        assert isinstance(cfg.app, AppSettingsConfig)
        assert isinstance(cfg.whisper, WhisperConfig)
        assert isinstance(cfg.model, ModelConfig)
        assert isinstance(cfg.openai_compatible, OpenAICompatibleConfig)
        assert isinstance(cfg.llm_api, LLMApiConfig)
        assert isinstance(cfg.ffmpeg, FFmpegConfig)
        assert isinstance(cfg.logging, LoggingConfig)

    def test_app_language_default(self):
        cfg = AppConfig()
        assert cfg.app.language == "en"

    def test_has_available_models_false_by_default(self):
        cfg = AppConfig()
        assert cfg.has_available_models() is False

    def test_has_available_models_true_when_models_exist(self):
        cfg = AppConfig(
            model=ModelConfig(available_translation_models=["facebook/m2m100_1.2B"])
        )
        assert cfg.has_available_models() is True

    def test_to_toml_dict_structure(self):
        cfg = AppConfig()
        d = cfg.to_toml_dict()
        # 顶层键应包含所有配置节
        assert "app" in d
        assert "whisper" in d
        assert "model" in d
        assert "openai_compatible" in d
        assert "llm_api" in d
        assert "ffmpeg" in d
        assert "logging" in d

    def test_to_toml_dict_whisper_section(self):
        cfg = AppConfig()
        d = cfg.to_toml_dict()
        whisper = d["whisper"]
        assert whisper["beam_size"] == 5
        assert whisper["word_timestamps"] is True

    def test_to_toml_dict_path_converted_to_string(self):
        """Path 类型字段应被转为字符串"""
        cfg = AppConfig()
        d = cfg.to_toml_dict()
        model = d["model"]
        assert isinstance(model["local_model_path"], str)

    def test_to_toml_dict_round_trip(self):
        """to_toml_dict 输出应可用于重建 AppConfig"""
        cfg = AppConfig(whisper=WhisperConfig(beam_size=7), llm_api=LLMApiConfig(timeout=60))
        d = cfg.to_toml_dict()
        # 用字典重建
        cfg2 = AppConfig(**d)
        assert cfg2.whisper.beam_size == 7
        assert cfg2.llm_api.timeout == 60
