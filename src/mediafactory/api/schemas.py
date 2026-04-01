"""
Pydantic 数据模型

定义 API 请求和响应的数据结构。
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== 枚举类型 ====================


class TaskType(str, Enum):
    """任务类型"""

    SUBTITLE = "subtitle"
    AUDIO = "audio"
    TRANSCRIBE = "transcribe"
    TRANSLATE = "translate"
    ENHANCE = "enhance"
    DOWNLOAD = "download"


class TaskStatus(str, Enum):
    """任务状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingStage(str, Enum):
    """处理阶段"""

    MODEL_LOADING = "model_loading"
    AUDIO_EXTRACTION = "audio_extraction"
    TRANSCRIPTION = "transcription"
    TRANSLATION = "translation"
    SRT_GENERATION = "srt_generation"
    VIDEO_ENHANCEMENT = "video_enhancement"


# ==================== 任务相关 ====================


class TaskConfig(BaseModel):
    """任务配置"""

    task_type: TaskType
    input_path: str
    input_text: Optional[str] = None
    output_path: Optional[str] = None

    # 语言设置
    source_lang: str = "auto"
    target_lang: str = "zh"

    # LLM 设置
    use_llm: bool = False
    llm_preset: str = "openai"

    # 音频设置
    audio_sample_rate: int = 48000
    audio_channels: int = 2
    audio_filter_enabled: bool = True
    audio_highpass_freq: int = 200
    audio_lowpass_freq: int = 3000
    audio_volume: float = 1.0
    audio_output_format: str = "wav"

    # 字幕设置
    output_format: str = "srt"  # srt, ass, txt
    bilingual: bool = False
    bilingual_layout: str = "translate_on_top"
    style_preset: str = "default"

    # 视频增强设置
    enhancement_scale: int = 4
    enhancement_model: str = "general"
    enhancement_denoise: bool = False
    enhancement_temporal: bool = False


class TaskProgress(BaseModel):
    """任务进度"""

    task_id: str
    status: TaskStatus
    progress: float = Field(ge=0, le=100)
    message: str = ""
    stage: Optional[ProcessingStage] = None

    # 批处理相关
    file_index: int = 0
    total_files: int = 1


class TaskResult(BaseModel):
    """任务结果"""

    task_id: str
    success: bool
    output_path: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskInfo(BaseModel):
    """任务完整信息"""

    id: str
    name: str
    config: TaskConfig
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    message: str = ""
    stage: Optional[ProcessingStage] = None
    result: Optional[TaskResult] = None


# ==================== 模型相关 ====================


class ModelType(str, Enum):
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
    preset: Optional[str] = None
    connection_available: Optional[bool] = None


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
    latency_ms: Optional[int] = None
    error: Optional[str] = None


# ==================== 配置相关 ====================


class WhisperConfigUpdate(BaseModel):
    """Whisper 配置更新"""

    beam_size: Optional[int] = Field(None, ge=1, le=10)
    patience: Optional[float] = Field(None, ge=0.0, le=10.0)
    length_penalty: Optional[float] = None
    no_speech_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    condition_on_previous_text: Optional[bool] = None
    word_timestamps: Optional[bool] = None
    vad_filter: Optional[bool] = None
    vad_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)


class LLMApiConfigUpdate(BaseModel):
    """LLM API 配置更新"""

    current_preset: Optional[str] = None
    timeout: Optional[int] = Field(None, ge=1, le=300)
    max_retries: Optional[int] = Field(None, ge=0, le=10)


class ConfigUpdate(BaseModel):
    """配置更新请求"""

    whisper: Optional[WhisperConfigUpdate] = None
    llm_api: Optional[LLMApiConfigUpdate] = None


# ==================== API 请求/响应 ====================


class SubtitleRequest(BaseModel):
    """字幕生成请求"""

    video_path: str
    output_path: Optional[str] = None
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
    output_path: Optional[str] = None
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
    output_path: Optional[str] = None
    source_lang: str = "auto"
    output_format: str = "srt"
    style_preset: str = "default"


class TranslateRequest(BaseModel):
    """翻译请求"""

    srt_path: Optional[str] = None
    text: Optional[str] = None
    source_lang: str = "auto"
    target_lang: str = "zh"
    use_llm: bool = False
    llm_preset: str = "openai"


class EnhanceRequest(BaseModel):
    """视频增强请求"""

    video_path: str
    output_path: Optional[str] = None
    scale: int = Field(default=4, ge=2, le=4)
    model_type: str = "general"
    denoise: bool = False
    temporal: bool = False


class TaskConfigUpdateRequest(BaseModel):
    """任务配置更新请求 - 仅允许修改可变参数（不含 task_type 和 input_path）"""

    output_path: Optional[str] = None
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None
    use_llm: Optional[bool] = None
    llm_preset: Optional[str] = None

    # 音频设置
    audio_sample_rate: Optional[int] = None
    audio_channels: Optional[int] = None
    audio_filter_enabled: Optional[bool] = None
    audio_highpass_freq: Optional[int] = None
    audio_lowpass_freq: Optional[int] = None
    audio_volume: Optional[float] = None
    audio_output_format: Optional[str] = None

    # 字幕设置
    output_format: Optional[str] = None
    bilingual: Optional[bool] = None
    bilingual_layout: Optional[str] = None
    style_preset: Optional[str] = None

    # 视频增强设置
    enhancement_scale: Optional[int] = None
    enhancement_model: Optional[str] = None
    enhancement_denoise: Optional[bool] = None
    enhancement_temporal: Optional[bool] = None


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
