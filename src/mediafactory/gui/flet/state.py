"""
响应式状态管理

实现观察者模式，支持状态变更通知。
"""

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
import asyncio
from pathlib import Path

from mediafactory.config import get_config, AppConfig
from mediafactory.logging import log_info, log_warning


class TaskStatus(Enum):
    """任务状态"""

    IDLE = "idle"
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskConfig:
    """任务配置"""

    task_type: str  # "audio", "transcription", "subtitle_translation", "subtitle"
    input_path: str
    source_lang: str = "auto"
    target_lang: str = "zh"
    use_llm: bool = False
    llm_preset: str = "openai"  # LLM 预设：openai, deepseek, glm, qwen, moonshot
    # 音频提取参数（默认最高质量）
    output_format: str = "wav"  # wav/mp3/flac
    sample_rate: int = 48000  # 采样率 Hz
    channels: int = 2  # 声道数 (1=单声道, 2=立体声)
    filter_enabled: bool = True  # 音频滤波器
    highpass_freq: int = 200  # 高通滤波频率 Hz
    lowpass_freq: int = 3000  # 低通滤波频率 Hz
    volume: float = 1.0  # 音量倍数
    # 转录/字幕输出格式
    output_format_type: str = "srt"  # "srt", "ass" 或 "txt"
    # 双语字幕选项
    bilingual: bool = False  # 是否生成双语字幕
    bilingual_layout: str = "translate_on_top"  # 双语布局
    # ASS字幕样式预设
    style_preset: str = "default"  # default, science, anime, news

    # 视频增强参数
    enhancement_scale: int = 4  # 2 或 4
    enhancement_model: str = "general"  # general 或 anime
    enhancement_denoise: bool = False
    enhancement_temporal: bool = False


@dataclass
class TaskItem:
    """任务项"""

    id: str
    name: str
    input_path: str
    output_path: Optional[str] = None
    status: TaskStatus = TaskStatus.IDLE
    progress: float = 0.0
    message: str = ""
    error: Optional[str] = None
    error_type: Optional[str] = None
    error_context: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    config: Optional[TaskConfig] = None


@dataclass
class ModelStatus:
    """模型状态"""

    model_type: str  # "whisper", "translation", "llm"
    name: str
    loaded: bool = False
    available: bool = False  # 是否可用（LLM 连通性）
    enabled: bool = True  # 是否启用（仅 LLM 有意义）


class AppState:
    """
    应用状态管理

    实现响应式状态，当状态变更时通知所有订阅者。
    """

    def __init__(self):
        self._listeners: List[Callable[[], None]] = []
        self._async_listeners: List[Callable[[], Any]] = []

        # 配置
        self._config: Optional[AppConfig] = None

        # 任务队列
        self._tasks: List[TaskItem] = []
        self._current_task: Optional[TaskItem] = None

        # 全局状态
        self._is_processing: bool = False
        self._is_paused: bool = False
        self._cancel_requested: bool = False

        # UI 状态
        self._current_page: str = "tasks"
        self._theme_mode: str = "system"

        # 模型状态
        self._whisper_status: Optional[ModelStatus] = None
        self._translation_status: Optional[ModelStatus] = None
        self._llm_status: Optional[ModelStatus] = None

        # 缓存
        self._cache: Dict[str, Any] = {}

    # ========== 属性访问 ==========

    @property
    def config(self) -> AppConfig:
        """获取配置"""
        if self._config is None:
            self._config = get_config()
        return self._config

    @property
    def tasks(self) -> List[TaskItem]:
        return self._tasks

    @property
    def current_task(self) -> Optional[TaskItem]:
        return self._current_task

    @property
    def is_processing(self) -> bool:
        return self._is_processing

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def cancel_requested(self) -> bool:
        return self._cancel_requested

    @property
    def current_page(self) -> str:
        return self._current_page

    @property
    def theme_mode(self) -> str:
        return self._theme_mode

    @property
    def whisper_status(self) -> Optional["ModelStatus"]:
        return self._whisper_status

    @property
    def translation_status(self) -> Optional["ModelStatus"]:
        return self._translation_status

    @property
    def llm_status(self) -> Optional["ModelStatus"]:
        return self._llm_status

    # ========== 状态更新方法 ==========

    def reload_config(self) -> None:
        """重新加载配置"""
        self._config = get_config()
        self.notify()

    def add_task(self, task: TaskItem) -> None:
        """添加任务"""
        self._tasks.append(task)
        self.notify()

    def remove_task(self, task_id: str) -> None:
        """移除任务"""
        self._tasks = [t for t in self._tasks if t.id != task_id]
        self.notify()

    def update_task(self, task_id: str, **kwargs) -> None:
        """更新任务状态"""
        for task in self._tasks:
            if task.id == task_id:
                for key, value in kwargs.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
                break
        self.notify()

    def clear_tasks(self) -> None:
        """清空任务列表"""
        self._tasks.clear()
        self.notify()

    def set_current_task(self, task: Optional[TaskItem]) -> None:
        """设置当前任务"""
        self._current_task = task
        self.notify()

    def start_processing(self) -> None:
        """开始处理"""
        self._is_processing = True
        self._is_paused = False
        self._cancel_requested = False
        self.notify()

    def pause_processing(self) -> None:
        """暂停处理"""
        self._is_paused = True
        self.notify()

    def resume_processing(self) -> None:
        """恢复处理"""
        self._is_paused = False
        self.notify()

    def stop_processing(self) -> None:
        """停止处理"""
        self._is_processing = False
        self._is_paused = False
        self.notify()

    def request_cancel(self) -> None:
        """请求取消"""
        self._cancel_requested = True
        self.notify()

    def clear_cancel(self) -> None:
        """清除取消请求"""
        self._cancel_requested = False
        self.notify()

    def set_current_page(self, page: str) -> None:
        """设置当前页面"""
        self._current_page = page
        self.notify()

    def set_theme_mode(self, mode: str) -> None:
        """设置主题模式"""
        self._theme_mode = mode
        self.notify()

    def set_whisper_status(self, status: "ModelStatus") -> None:
        """设置 Whisper 模型状态"""
        self._whisper_status = status
        self.notify()

    def set_translation_status(self, status: "ModelStatus") -> None:
        """设置翻译模型状态"""
        self._translation_status = status
        self.notify()

    def set_llm_status(self, status: "ModelStatus") -> None:
        """设置 LLM 状态"""
        self._llm_status = status
        self.notify()

    def set_cache(self, key: str, value: Any) -> None:
        """设置缓存"""
        self._cache[key] = value

    def get_cache(self, key: str, default: Any = None) -> Any:
        """获取缓存"""
        return self._cache.get(key, default)

    def clear_cache(self, key: Optional[str] = None) -> None:
        """清除缓存"""
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()

    # ========== 观察者模式 ==========

    def subscribe(self, callback: Callable[[], None]) -> None:
        """订阅状态变更（同步）"""
        self._listeners.append(callback)

    def subscribe_async(self, callback: Callable[[], Any]) -> None:
        """订阅状态变更（异步）"""
        self._async_listeners.append(callback)

    def unsubscribe(self, callback: Callable[[], None]) -> None:
        """取消订阅"""
        if callback in self._listeners:
            self._listeners.remove(callback)
        if callback in self._async_listeners:
            self._async_listeners.remove(callback)

    def notify(self) -> None:
        """通知所有订阅者"""
        # 同步回调
        for callback in self._listeners:
            try:
                callback()
            except Exception as e:
                log_warning(f"状态通知回调失败: {e}")

        # 异步回调需要在外部处理
        # 不能在这里直接 await，因为 notify 可能不在异步上下文中


# ==================== 单例管理 ====================

# 全局状态实例和锁
_state_instance: Optional[AppState] = None
_state_lock = threading.Lock()


def get_state() -> AppState:
    """获取全局状态实例（线程安全）"""
    global _state_instance
    if _state_instance is None:
        with _state_lock:
            if _state_instance is None:
                _state_instance = AppState()
    return _state_instance


def reset_state() -> None:
    """重置状态（用于测试）"""
    global _state_instance
    with _state_lock:
        _state_instance = None
