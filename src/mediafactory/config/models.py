"""Configuration models using Pydantic v2.

配置结构定义，使用 Pydantic BaseModel 实现类型安全。
默认值直接定义在 Field 中，便于维护。
"""

from pathlib import Path
from typing import Any, Dict, List

from pydantic import BaseModel, Field


# ============================================================================
# Whisper 配置
# ============================================================================


class WhisperConfig(BaseModel):
    """Whisper 语音识别配置

    以下参数已写死在 engine/recognition.py 中（调参意义不大）：
    - patience=1.0 (Beam search 标准值)
    - length_penalty=1.0 (Whisper 官方推荐)
    - vad_speech_pad_ms=200 (Silero VAD 推荐值)
    """

    beam_size: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Beam search 宽度",
    )
    no_speech_threshold: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="静音检测阈值",
    )
    condition_on_previous_text: bool = Field(
        default=False,
        description="是否基于前文进行条件生成",
    )
    word_timestamps: bool = Field(
        default=True,
        description="提取词级时间戳",
    )

    # VAD (Voice Activity Detection) 配置
    vad_filter: bool = Field(
        default=True,
        description="启用 VAD 过滤非语音段落",
    )
    vad_threshold: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="VAD 敏感度（越高检测到的语音越少）",
    )
    vad_min_speech_duration_ms: int = Field(
        default=250,
        ge=0,
        le=10000,
        description="最短语音段落时长（毫秒）",
    )
    vad_min_silence_duration_ms: int = Field(
        default=500,
        ge=0,
        le=10000,
        description="分割语音段落的最短静音时长（毫秒）",
    )


# ============================================================================
# 后处理配置（智能断句 + 说话人分离）
# ============================================================================


class PostProcessConfig(BaseModel):
    """Whisper 转录后处理配置"""

    resegment_enabled: bool = Field(
        default=True,
        description="启用智能断句（stable-ts regroup）",
    )
    max_chars_cjk: int = Field(
        default=42,
        ge=10,
        le=200,
        description="CJK 单条字幕最大字符数",
    )
    max_chars_latin: int = Field(
        default=80,
        ge=10,
        le=300,
        description="Latin 单条字幕最大字符数",
    )
    min_duration: float = Field(
        default=1.0,
        ge=0.1,
        le=5.0,
        description="最短持续时间（秒）",
    )
    max_duration: float = Field(
        default=7.0,
        ge=2.0,
        le=30.0,
        description="最长持续时间（秒）",
    )
    merge_gap_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="合并间隔阈值（秒）",
    )

    # 说话人分离
    diarization_enabled: bool = Field(
        default=False,
        description="启用说话人分离（需要 pyannote 模型）",
    )
    num_speakers: int = Field(
        default=0,
        ge=0,
        le=20,
        description="说话人数量（0=自动检测）",
    )


# ============================================================================
# Model 配置
# ============================================================================


class ModelConfig(BaseModel):
    """模型存储和发现配置"""

    local_model_path: Path = Field(
        default=Path("./models"),
        description="本地模型存储目录",
    )
    download_source: str = Field(
        default="https://hf-mirror.com",
        description="模型下载源 URL",
    )
    download_timeout: int = Field(
        default=30,
        ge=10,
        le=600,
        description="模型下载 HTTP 请求超时（秒）",
    )
    hf_token: str = Field(
        default="",
        description="HuggingFace Access Token（用于 gated 模型如 pyannote）",
    )
    available_translation_models: List[str] = Field(
        default_factory=list,
        description="已下载的翻译模型列表",
    )
    whisper_models: List[str] = Field(
        default_factory=list,
        description="已下载的 Whisper 模型列表",
    )


# ============================================================================
# LLM API 配置
# ============================================================================


class PresetServiceConfig(BaseModel):
    """单个预设服务配置

    每个预设（openai, deepseek, glm, qwen, moonshot, custom）都有独立配置。
    """

    api_key: str = Field(
        default="",
        description="API 密钥",
    )
    base_url: str = Field(
        default="",
        description="API 基础 URL",
    )
    model: str = Field(
        default="",
        description="使用的模型",
    )
    connection_available: bool = Field(
        default=False,
        description="连接测试是否通过",
    )


class OpenAICompatibleConfig(BaseModel):
    """统一的 OpenAI 兼容 API 配置

    支持所有 OpenAI 兼容服务：
    - OpenAI (官方)
    - DeepSeek
    - GLM (智谱AI)
    - 通义千问 (Qwen)
    - Moonshot
    - 自定义服务

    TOML 配置格式：
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

    current_preset: str = Field(
        default="openai",
        description="当前激活的预设",
    )

    # 各预设配置
    openai: PresetServiceConfig = Field(
        default_factory=PresetServiceConfig,
        description="OpenAI 配置",
    )
    deepseek: PresetServiceConfig = Field(
        default_factory=PresetServiceConfig,
        description="DeepSeek 配置",
    )
    glm: PresetServiceConfig = Field(
        default_factory=PresetServiceConfig,
        description="GLM (智谱AI) 配置",
    )
    qwen: PresetServiceConfig = Field(
        default_factory=PresetServiceConfig,
        description="Qwen (通义千问) 配置",
    )
    moonshot: PresetServiceConfig = Field(
        default_factory=PresetServiceConfig,
        description="Moonshot AI 配置",
    )
    custom: PresetServiceConfig = Field(
        default_factory=PresetServiceConfig,
        description="自定义服务配置",
    )

    _VALID_PRESETS = {"openai", "deepseek", "glm", "qwen", "moonshot", "custom"}

    def get_preset_config(self, preset: str) -> PresetServiceConfig:
        """获取指定预设的配置"""
        if preset not in self._VALID_PRESETS:
            raise ValueError(f"Unknown preset: {preset}")
        return getattr(self, preset)


class LLMApiConfig(BaseModel):
    """LLM API 通用配置"""

    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="请求超时（秒）",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="最大重试次数",
    )
    batch_size: int = Field(
        default=40,
        ge=1,
        le=200,
        description="批量翻译批次大小",
    )
    split_threshold: int = Field(
        default=10,
        ge=1,
        le=100,
        description="低于此数量不进行二分降级",
    )
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="LLM 生成温度，越低越确定，越高越多样",
    )


# ============================================================================
# FFmpeg 配置
# ============================================================================


class FFmpegConfig(BaseModel):
    """FFmpeg 子进程超时配置"""

    soft_subtitle_timeout: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="软字幕嵌入超时（秒）",
    )
    hard_subtitle_timeout: int = Field(
        default=1800,
        ge=300,
        le=7200,
        description="硬字幕烧录超时（秒）",
    )
    multi_subtitle_timeout: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="多字幕嵌入超时（秒）",
    )


# ============================================================================
# 日志配置
# ============================================================================


class LoggingConfig(BaseModel):
    """日志清理配置"""

    retention_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="日志保留天数",
    )
    max_files: int = Field(
        default=20,
        ge=1,
        le=100,
        description="最多保留日志文件数",
    )


# ============================================================================
# 根配置
# ============================================================================


class AppSettingsConfig(BaseModel):
    """应用设置"""

    language: str = Field(
        default="en",
        description="界面语言",
    )


class AppConfig(BaseModel):
    """根配置对象

    访问模式：
        config.whisper.beam_size
        config.model.local_model_path
        config.openai_compatible.openai.api_key
    """

    # 应用设置
    app: AppSettingsConfig = Field(
        default_factory=AppSettingsConfig,
        description="应用设置",
    )

    # 嵌套配置节
    whisper: WhisperConfig = Field(
        default_factory=WhisperConfig,
        description="Whisper 语音识别配置",
    )
    postprocess: PostProcessConfig = Field(
        default_factory=PostProcessConfig,
        description="转录后处理配置",
    )
    model: ModelConfig = Field(
        default_factory=ModelConfig,
        description="模型存储和发现配置",
    )
    openai_compatible: OpenAICompatibleConfig = Field(
        default_factory=OpenAICompatibleConfig,
        description="统一的 OpenAI 兼容 API 配置",
    )
    llm_api: LLMApiConfig = Field(
        default_factory=LLMApiConfig,
        description="LLM API 通用配置",
    )
    ffmpeg: FFmpegConfig = Field(
        default_factory=FFmpegConfig,
        description="FFmpeg 子进程超时配置",
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="日志清理配置",
    )

    def has_available_models(self) -> bool:
        """检查是否有可用的翻译模型"""
        return len(self.model.available_translation_models) > 0

    def to_toml_dict(self) -> Dict[str, Any]:
        """转换为 TOML 兼容的字典"""
        result = {}
        for section_name in self.model_fields:
            section = getattr(self, section_name)
            if hasattr(section, "model_dump"):
                section_dict = section.model_dump(mode="json", exclude_none=True)
            else:
                section_dict = section

            # Path 转字符串
            for key, value in section_dict.items() if isinstance(section_dict, dict) else []:
                if isinstance(value, Path):
                    section_dict[key] = str(value)

            if section_dict:
                result[section_name] = section_dict
        return result
