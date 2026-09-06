"""
Pydantic 数据模型

定义 API 请求和响应的数据结构。
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

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

    # 输出格式
    output_format: str = "srt"  # srt, ass, vtt, txt

    # 分类型配置（按任务类型使用）
    audio_config: AudioConfig | None = None
    subtitle_config: SubtitleConfig | None = None
    enhancement_config: EnhancementConfig | None = None


class TaskProgress(BaseModel):
    """任务进度"""

    task_id: str
    status: TaskStatus
    progress: float = Field(ge=0, le=100)
    message: str = ""
    stage: ProcessingStage | None = None


class TaskResult(BaseModel):
    """任务结果"""

    task_id: str
    success: bool
    output_path: str | None = None
    error: str | None = None
    error_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ==================== 模型相关 ====================


class ModelType(StrEnum):
    """模型类型"""

    WHISPER = "whisper"
    TRANSLATION = "translation"
    LLM = "llm"


class ModelStatus(BaseModel):
    """模型状态"""

    model_type: ModelType
    name: str
    loaded: bool = False
    available: bool = False
    enabled: bool = True

    # LLM 特有
    preset: str | None = None
    connection_available: bool | None = None


class TranslationModelInfo(BaseModel):
    """翻译模型信息"""

    id: str
    name: str
    tier: str  # Small, Medium, Large
    memory: str
    downloaded: bool = False


class LLMTestResult(BaseModel):
    """LLM 连接测试结果"""

    preset: str
    success: bool
    latency_ms: int | None = None
    error: str | None = None


# ==================== 配置相关 ====================


class WhisperConfigUpdate(BaseModel):
    """Whisper 配置更新"""

    beam_size: int | None = Field(None, ge=1, le=10)
    patience: float | None = Field(None, ge=0.0, le=10.0)
    length_penalty: float | None = None
    no_speech_threshold: float | None = Field(None, ge=0.0, le=1.0)
    condition_on_previous_text: bool | None = None
    word_timestamps: bool | None = None
    vad_filter: bool | None = None
    vad_threshold: float | None = Field(None, ge=0.0, le=1.0)


class LLMApiConfigUpdate(BaseModel):
    """LLM API 配置更新"""

    current_preset: str | None = None
    timeout: int | None = Field(None, ge=1, le=300)
    max_retries: int | None = Field(None, ge=0, le=10)


class ConfigUpdate(BaseModel):
    """配置更新请求"""

    whisper: WhisperConfigUpdate | None = None
    llm_api: LLMApiConfigUpdate | None = None


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


class EnhanceRequest(BaseModel):
    """视频增强请求"""

    video_path: str
    output_path: str | None = None
    scale: int = Field(default=4, ge=2, le=4)
    model_type: str = "general"
    denoise: bool = False
    temporal: bool = False


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


# ==================== WebSocket 消息 ====================


class WSMessage(BaseModel):
    """WebSocket 消息基类"""

    type: str


class WSSubscribe(WSMessage):
    """订阅任务进度"""

    type: str = "subscribe"
    task_id: str


class WSProgress(WSMessage):
    """进度推送"""

    type: str = "progress"
    task_id: str
    data: TaskProgress


class WSTaskComplete(WSMessage):
    """任务完成"""

    type: str = "task_complete"
    task_id: str
    data: TaskResult
