"""
Pydantic 数据模型

定义 API 请求和响应的数据结构。
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ==================== 枚举类型 ====================


class TaskType(StrEnum):
    """任务类型"""

    SUBTITLE = "subtitle"
    AUDIO = "audio"
    TRANSCRIBE = "transcribe"
    TRANSLATE = "translate"
    ENHANCE = "enhance"
    DOWNLOAD = "download"


class TaskStatus(StrEnum):
    """任务状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingStage(StrEnum):
    """处理阶段"""

    MODEL_LOADING = "model_loading"
    AUDIO_EXTRACTION = "audio_extraction"
    TRANSCRIPTION = "transcription"
    TRANSLATION = "translation"
    SRT_GENERATION = "srt_generation"
    VIDEO_ENHANCEMENT = "video_enhancement"


# ==================== 任务相关 ====================


class AudioConfig(BaseModel):
    """音频处理配置"""

    sample_rate: int = Field(default=48000, ge=16000, le=96000)
    channels: int = Field(default=2, ge=1, le=2)
    filter_enabled: bool = True
    highpass_freq: int = Field(default=200, ge=20, le=500)
    lowpass_freq: int = Field(default=3000, ge=1000, le=16000)
    volume: float = Field(default=1.0, ge=0.1, le=2.0)
    output_format: str = "wav"


class SubtitleConfig(BaseModel):
    """字幕生成配置"""

    output_format: str = "srt"  # srt, ass, vtt, txt
    bilingual: bool = False
    bilingual_layout: str = "translate_on_top"
    style_preset: str = "default"


class EnhancementConfig(BaseModel):
    """视频增强配置"""

    scale: int = Field(default=4, ge=2, le=4)
    model: str = "general"
    denoise: bool = False
    temporal: bool = False
    face_restore: bool = False  # 老片增强 P0：CodeFormer 人脸修复
    film_grain: bool = False  # 老片增强 P0：胶片颗粒后处理


class TaskConfig(BaseModel):
    """任务配置"""

    task_type: TaskType
    input_path: str
    input_text: str | None = None
    output_path: str | None = None

    # 语言设置
    source_lang: str = "auto"
    target_lang: str = "zh"

    # LLM 设置
    use_llm: bool = False
    llm_preset: str = "openai"

    # 用户术语表（源词→译法），翻译时强制生效
    terminology: dict[str, str] | None = Field(default=None)

    @field_validator("terminology")
    @classmethod
    def _validate_terminology(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        if v is None:
            return v
        if len(v) > 200:
            raise ValueError("terminology exceeds 200 entries")
        for key, value in v.items():
            if len(key) > 200 or len(value) > 200:
                raise ValueError("terminology entry exceeds 200 characters")
        return v

    # 本地兜底模型（Ollama）；None = 不兜底
    fallback_model: str | None = Field(default=None)

    @field_validator("fallback_model")
    @classmethod
    def _validate_fallback_model(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v or len(v) > 200:
            raise ValueError("fallback_model must be 1-200 characters")
        return v

    # 输出格式
    output_format: str = "srt"  # srt, ass, vtt, txt

    # 分类型配置（按任务类型使用）
    audio_config: AudioConfig | None = None
    subtitle_config: SubtitleConfig | None = None
    enhancement_config: EnhancementConfig | None = None


class TaskResult(BaseModel):
    """任务结果"""

    task_id: str
    success: bool
    output_path: str | None = None
    error: str | None = None
    error_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ==================== API 请求/响应 ====================


class SubtitleRequest(BaseModel):
    """字幕生成请求"""

    video_path: str
    output_path: str | None = None
    source_lang: str = "auto"
    target_lang: str = "zh"
    use_llm: bool = False
    llm_preset: str = "openai"
    output_format: str = "srt"
    bilingual: bool = False
    bilingual_layout: str = "translate_on_top"
    style_preset: str = "default"
    terminology: dict[str, str] | None = None

    @field_validator("terminology")
    @classmethod
    def _validate_request_terminology(
        cls, v: dict[str, str] | None
    ) -> dict[str, str] | None:
        if v is None:
            return v
        if len(v) > 200:
            raise ValueError("terminology exceeds 200 entries")
        for key, value in v.items():
            if len(key) > 200 or len(value) > 200:
                raise ValueError("terminology entry exceeds 200 characters")
        return v

    fallback_model: str | None = None

    @field_validator("fallback_model")
    @classmethod
    def _validate_subtitle_request_fallback_model(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v or len(v) > 200:
            raise ValueError("fallback_model must be 1-200 characters")
        return v


class AudioRequest(BaseModel):
    """音频提取请求"""

    video_path: str
    output_path: str | None = None
    output_format: str = "wav"
    sample_rate: int = 48000
    channels: int = 2
    filter_enabled: bool = True
    highpass_freq: int = 200
    lowpass_freq: int = 3000
    volume: float = 1.0


class TranscribeRequest(BaseModel):
    """转录请求"""

    audio_path: str
    output_path: str | None = None
    source_lang: str = "auto"
    output_format: str = "srt"  # srt, ass, vtt, txt
    style_preset: str = "default"


class TranslateRequest(BaseModel):
    """翻译请求"""

    srt_path: str | None = None
    text: str | None = None
    source_lang: str = "auto"
    target_lang: str = "zh"
    output_format: str = "srt"  # srt, ass, vtt, txt
    use_llm: bool = False
    llm_preset: str = "openai"
    terminology: dict[str, str] | None = None

    @field_validator("terminology")
    @classmethod
    def _validate_request_terminology(
        cls, v: dict[str, str] | None
    ) -> dict[str, str] | None:
        if v is None:
            return v
        if len(v) > 200:
            raise ValueError("terminology exceeds 200 entries")
        for key, value in v.items():
            if len(key) > 200 or len(value) > 200:
                raise ValueError("terminology entry exceeds 200 characters")
        return v

    fallback_model: str | None = None

    @field_validator("fallback_model")
    @classmethod
    def _validate_translate_request_fallback_model(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v or len(v) > 200:
            raise ValueError("fallback_model must be 1-200 characters")
        return v


class EnhanceRequest(BaseModel):
    """视频增强请求"""

    video_path: str
    output_path: str | None = None
    scale: int = Field(default=4, ge=2, le=4)
    model_type: str = "general"
    denoise: bool = False
    temporal: bool = False
    face_restore: bool = False
    film_grain: bool = False


class TaskConfigUpdateRequest(BaseModel):
    """任务配置更新请求 - 仅允许修改可变参数（不含 task_type 和 input_path）"""

    output_path: str | None = None
    source_lang: str | None = None
    target_lang: str | None = None
    use_llm: bool | None = None
    llm_preset: str | None = None

    # 分类型配置更新
    audio_config: AudioConfig | None = None
    subtitle_config: SubtitleConfig | None = None
    enhancement_config: EnhancementConfig | None = None


class TaskResponse(BaseModel):
    """任务创建响应"""

    task_id: str
    status: TaskStatus
    message: str = "Task created, waiting to start"


class CancelResponse(BaseModel):
    """取消任务响应"""

    task_id: str
    status: str
    message: str = "Cancellation requested"
