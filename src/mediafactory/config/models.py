"""Configuration models using Pydantic v2.

This module defines all configuration structures using Pydantic BaseSettings.
Supports environment variable overrides with MF_ prefix.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .defaults import (
    DEFAULT_DOWNLOAD_SOURCE,
    DEFAULT_LLM_MAX_CHARS_PER_REQUEST,
    DEFAULT_LLM_MAX_RETRIES,
    DEFAULT_LLM_MAX_SEGMENTS_PER_REQUEST,
    DEFAULT_LLM_RATE_LIMIT_ENABLED,
    DEFAULT_LLM_RATE_LIMIT_PER_SECOND,
    DEFAULT_LLM_TIMEOUT,
    DEFAULT_MODEL_DOWNLOAD_TIMEOUT,
    DEFAULT_MODELS_PATH,
    DEFAULT_OPENAI_COMPATIBLE_BASE_URL,
    DEFAULT_OPENAI_COMPATIBLE_MODEL,
    DEFAULT_OPENAI_COMPATIBLE_PRESET,
    DEFAULT_WHISPER_BEAM_SIZE,
    DEFAULT_WHISPER_CONDITION_ON_PREVIOUS_TEXT,
    DEFAULT_WHISPER_LENGTH_PENALTY,
    DEFAULT_WHISPER_NO_SPEECH_THRESHOLD,
    DEFAULT_WHISPER_PATIENCE,
    DEFAULT_WHISPER_VAD_FILTER,
    DEFAULT_WHISPER_VAD_MIN_SILENCE_DURATION_MS,
    DEFAULT_WHISPER_VAD_MIN_SPEECH_DURATION_MS,
    DEFAULT_WHISPER_VAD_SPEECH_PAD_MS,
    DEFAULT_WHISPER_VAD_THRESHOLD,
    DEFAULT_WHISPER_WORD_TIMESTAMPS,
    ValidationConstraints,
)


class WhisperConfig(BaseSettings):
    """Whisper speech recognition settings.

    Environment variables:
        MF_WHISPER_BEAM_SIZE: Beam size for transcription (1-10)
        MF_WHISPER_PATIENCE: Patience for beam search (0.0-10.0)
        MF_WHISPER_LENGTH_PENALTY: Length penalty for beam search
        MF_WHISPER_NO_SPEECH_THRESHOLD: Speech sensitivity (0.0-1.0)
        MF_WHISPER_CONDITION_ON_PREVIOUS_TEXT: Condition on previous text
        MF_WHISPER_WORD_TIMESTAMPS: Extract word-level timestamps
        MF_WHISPER_VAD_FILTER: Enable VAD filtering
        MF_WHISPER_VAD_THRESHOLD: VAD sensitivity threshold
        MF_WHISPER_VAD_MIN_SPEECH_DURATION_MS: Min speech duration in ms
        MF_WHISPER_VAD_MIN_SILENCE_DURATION_MS: Min silence for segment split
        MF_WHISPER_VAD_SPEECH_PAD_MS: Padding around speech segments
    """

    model_config = SettingsConfigDict(
        env_prefix="MF_WHISPER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    beam_size: int = Field(
        default=DEFAULT_WHISPER_BEAM_SIZE,
        ge=ValidationConstraints.WHISPER_BEAM_SIZE_MIN,
        le=ValidationConstraints.WHISPER_BEAM_SIZE_MAX,
        description="Beam size for transcription",
    )
    patience: float = Field(
        default=DEFAULT_WHISPER_PATIENCE,
        ge=ValidationConstraints.WHISPER_PATIENCE_MIN,
        le=ValidationConstraints.WHISPER_PATIENCE_MAX,
        description="Patience for beam search",
    )
    length_penalty: float = Field(
        default=DEFAULT_WHISPER_LENGTH_PENALTY,
        description="Length penalty for beam search",
    )
    no_speech_threshold: float = Field(
        default=DEFAULT_WHISPER_NO_SPEECH_THRESHOLD,
        ge=ValidationConstraints.WHISPER_NO_SPEECH_THRESHOLD_MIN,
        le=ValidationConstraints.WHISPER_NO_SPEECH_THRESHOLD_MAX,
        description="Speech sensitivity threshold",
    )
    condition_on_previous_text: bool = Field(
        default=DEFAULT_WHISPER_CONDITION_ON_PREVIOUS_TEXT,
        description="Condition on previous text",
    )
    word_timestamps: bool = Field(
        default=DEFAULT_WHISPER_WORD_TIMESTAMPS,
        description="Extract word-level timestamps",
    )

    # VAD (Voice Activity Detection) settings
    vad_filter: bool = Field(
        default=DEFAULT_WHISPER_VAD_FILTER,
        description="Enable VAD to filter non-speech segments",
    )
    vad_threshold: float = Field(
        default=DEFAULT_WHISPER_VAD_THRESHOLD,
        ge=ValidationConstraints.WHISPER_VAD_THRESHOLD_MIN,
        le=ValidationConstraints.WHISPER_VAD_THRESHOLD_MAX,
        description="VAD sensitivity (0.0-1.0, higher = less speech detected)",
    )
    vad_min_speech_duration_ms: int = Field(
        default=DEFAULT_WHISPER_VAD_MIN_SPEECH_DURATION_MS,
        ge=ValidationConstraints.WHISPER_VAD_MIN_SPEECH_DURATION_MS_MIN,
        le=ValidationConstraints.WHISPER_VAD_MIN_SPEECH_DURATION_MS_MAX,
        description="Minimum speech segment duration in milliseconds",
    )
    vad_min_silence_duration_ms: int = Field(
        default=DEFAULT_WHISPER_VAD_MIN_SILENCE_DURATION_MS,
        ge=ValidationConstraints.WHISPER_VAD_MIN_SILENCE_DURATION_MS_MIN,
        le=ValidationConstraints.WHISPER_VAD_MIN_SILENCE_DURATION_MS_MAX,
        description="Minimum silence duration for segment split in milliseconds",
    )
    vad_speech_pad_ms: int = Field(
        default=DEFAULT_WHISPER_VAD_SPEECH_PAD_MS,
        ge=ValidationConstraints.WHISPER_VAD_SPEECH_PAD_MS_MIN,
        le=ValidationConstraints.WHISPER_VAD_SPEECH_PAD_MS_MAX,
        description="Padding around speech segments in milliseconds",
    )


class ModelConfig(BaseSettings):
    """Model storage and discovery settings.

    Environment variables:
        MF_MODEL_LOCAL_MODEL_PATH: Local model storage path
        MF_MODEL_DOWNLOAD_SOURCE: Model download source URL
        MF_MODEL_DOWNLOAD_TIMEOUT: HTTP request timeout for downloads (seconds)
    """

    model_config = SettingsConfigDict(
        env_prefix="MF_MODEL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    local_model_path: Path = Field(
        default=DEFAULT_MODELS_PATH,
        description="Local model storage directory",
    )
    download_source: str = Field(
        default=DEFAULT_DOWNLOAD_SOURCE,
        description="Model download source URL",
    )
    download_timeout: int = Field(
        default=DEFAULT_MODEL_DOWNLOAD_TIMEOUT,
        ge=ValidationConstraints.MODEL_DOWNLOAD_TIMEOUT_MIN,
        le=ValidationConstraints.MODEL_DOWNLOAD_TIMEOUT_MAX,
        description="HTTP request timeout for model downloads (seconds)",
    )
    available_translation_models: List[str] = Field(
        default_factory=list,
        description="List of downloaded translation models",
    )
    whisper_models: List[str] = Field(
        default_factory=list,
        description="List of downloaded Whisper models",
    )


class PresetServiceConfig(BaseSettings):
    """Configuration for a single preset service.

    Each preset (openai, deepseek, glm, qwen, moonshot, custom) has its own config.
    """

    model_config = SettingsConfigDict(
        env_prefix="MF_PRESET_",  # Won't be used directly, for documentation
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: str = Field(
        default="",
        description="API key for this preset",
    )
    base_url: str = Field(
        default="",
        description="API base URL for this preset",
    )
    model: str = Field(
        default="",
        description="Model to use for this preset",
    )
    connection_available: bool = Field(
        default=False,
        description="Whether the connection test passed",
    )


class OpenAICompatibleConfig(BaseSettings):
    """Unified OpenAI-compatible API configuration.

    Supports all OpenAI-compatible services with per-preset configuration:
    - OpenAI (official)
    - DeepSeek
    - GLM (智谱AI)
    - 通义千问 (Qwen)
    - Moonshot
    - Custom services

    Config format in TOML:
        [openai_compatible]
        current_preset = "glm"

        [openai_compatible.openai]
        api_key = "sk-xxx"
        base_url = "https://api.openai.com/v1"
        model = "gpt-4o-mini"

        [openai_compatible.glm]
        api_key = "your-glm-key"
        base_url = "https://open.bigmodel.cn/api/paas/v4"
        model = "glm-4-flash"
    """

    model_config = SettingsConfigDict(
        env_prefix="MF_OPENAI_COMPATIBLE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    current_preset: str = Field(
        default=DEFAULT_OPENAI_COMPATIBLE_PRESET,
        description="Current active preset (openai, deepseek, glm, qwen, moonshot, custom)",
    )

    # Per-preset configurations
    openai: PresetServiceConfig = Field(
        default_factory=PresetServiceConfig,
        description="OpenAI configuration",
    )
    deepseek: PresetServiceConfig = Field(
        default_factory=PresetServiceConfig,
        description="DeepSeek configuration",
    )
    glm: PresetServiceConfig = Field(
        default_factory=PresetServiceConfig,
        description="GLM (智谱AI) configuration",
    )
    qwen: PresetServiceConfig = Field(
        default_factory=PresetServiceConfig,
        description="Qwen (通义千问) configuration",
    )
    moonshot: PresetServiceConfig = Field(
        default_factory=PresetServiceConfig,
        description="Moonshot AI configuration",
    )
    custom: PresetServiceConfig = Field(
        default_factory=PresetServiceConfig,
        description="Custom service configuration",
    )

    def get_preset_config(self, preset: str) -> PresetServiceConfig:
        """Get configuration for a specific preset."""
        return getattr(self, preset, PresetServiceConfig())


class LLMApiConfig(BaseSettings):
    """Unified LLM API settings.

    Environment variables:
        MF_LLM_API_TIMEOUT: Request timeout in seconds
        MF_LLM_API_MAX_RETRIES: Max retry attempts
        MF_LLM_API_RATE_LIMIT_ENABLED: Enable rate limiting
        MF_LLM_API_RATE_LIMIT_PER_SECOND: Rate limit
        MF_LLM_API_MAX_CHARS_PER_REQUEST: Max chars per request
        MF_LLM_API_MAX_SEGMENTS_PER_REQUEST: Max segments per request
        MF_LLM_API_MAX_TOKENS: Max output tokens
    """

    model_config = SettingsConfigDict(
        env_prefix="MF_LLM_API_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    timeout: int = Field(
        default=DEFAULT_LLM_TIMEOUT,
        ge=ValidationConstraints.LLM_TIMEOUT_MIN,
        le=ValidationConstraints.LLM_TIMEOUT_MAX,
        description="Request timeout in seconds",
    )
    max_retries: int = Field(
        default=DEFAULT_LLM_MAX_RETRIES,
        ge=ValidationConstraints.LLM_MAX_RETRIES_MIN,
        le=ValidationConstraints.LLM_MAX_RETRIES_MAX,
        description="Max retry attempts",
    )
    rate_limit_enabled: bool = Field(
        default=DEFAULT_LLM_RATE_LIMIT_ENABLED,
        description="Enable rate limiting",
    )
    rate_limit_per_second: float = Field(
        default=DEFAULT_LLM_RATE_LIMIT_PER_SECOND,
        ge=ValidationConstraints.LLM_RATE_LIMIT_MIN,
        le=ValidationConstraints.LLM_RATE_LIMIT_MAX,
        description="Rate limit per second",
    )
    max_chars_per_request: int = Field(
        default=DEFAULT_LLM_MAX_CHARS_PER_REQUEST,
        ge=ValidationConstraints.LLM_MAX_CHARS_MIN,
        le=ValidationConstraints.LLM_MAX_CHARS_MAX,
        description="Max chars per request",
    )
    max_segments_per_request: int = Field(
        default=DEFAULT_LLM_MAX_SEGMENTS_PER_REQUEST,
        ge=ValidationConstraints.LLM_MAX_SEGMENTS_MIN,
        le=ValidationConstraints.LLM_MAX_SEGMENTS_MAX,
        description="Max segments per request",
    )


class AppConfig(BaseSettings):
    """Root configuration object.

    This is the main configuration class that contains all nested
    configuration sections.

    Access pattern:
        config.whisper.beam_size
        config.model.local_model_path
        config.openai_compatible.api_key

    Environment variable overrides:
        MF_WHISPER_BEAM_SIZE=7
        MF_MODEL_LOCAL_MODEL_PATH=/path/to/models
        MF_OPENAI_COMPATIBLE_API_KEY=sk-...
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Nested configuration sections
    whisper: WhisperConfig = Field(
        default_factory=WhisperConfig,
        description="Whisper speech recognition settings",
    )
    model: ModelConfig = Field(
        default_factory=ModelConfig,
        description="Model storage and discovery settings",
    )
    openai_compatible: OpenAICompatibleConfig = Field(
        default_factory=OpenAICompatibleConfig,
        description="Unified OpenAI-compatible API configuration",
    )
    llm_api: LLMApiConfig = Field(
        default_factory=LLMApiConfig,
        description="Unified LLM API settings",
    )

    def has_available_models(self) -> bool:
        """Check if translation models are available.

        Returns:
            True if there are available translation models.
        """
        return len(self.model.available_translation_models) > 0

    def to_toml_dict(self) -> Dict[str, Any]:
        """Convert configuration to TOML-compatible dictionary.

        Returns:
            Dictionary suitable for TOML serialization.
        """
        result = {}
        for section_name in self.model_fields:
            section = getattr(self, section_name)
            if hasattr(section, "model_dump"):
                result[section_name] = section.model_dump(mode="json")
            else:
                result[section_name] = section
        return result
