"""MediaFactory 模型资源管理。

提供上下文管理器，确保 Faster Whisper 模型正确释放，
解决信号量泄漏问题。
"""

import gc
import signal
import atexit
import threading
from contextlib import contextmanager
from typing import Optional

from .logging import log_info, log_warning


class ModelResourceManager:
    """模型资源管理器（单例）。

    负责管理 Faster Whisper 模型的生命周期，确保资源正确释放。
    使用 __new__ 方法实现单例，在 CPython 中是线程安全的。
    """

    _instance: Optional["ModelResourceManager"] = None
    _lock = threading.Lock()
    _initialized: bool = False  # 防止重复初始化
    _model = None
    _original_signals = {}

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化模型资源管理器。"""
        # 防止重复初始化
        if ModelResourceManager._initialized:
            return
        ModelResourceManager._initialized = True
        self._setup_signal_handlers()
        atexit.register(self.cleanup)

    def _setup_signal_handlers(self):
        """设置信号处理器。"""
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                self._original_signals[sig] = signal.getsignal(sig)
                signal.signal(sig, self._signal_handler)
            except (ValueError, AttributeError):
                # 某些平台可能不支持所有信号
                pass

    def _signal_handler(self, signum, frame):
        """Signal handler function."""
        log_info(f"Received signal {signum}, cleaning up resources...")
        self.cleanup()

        # 恢复原始信号处理
        if signum in self._original_signals:
            signal.signal(signum, self._original_signals[signum])

        if signum == signal.SIGINT:
            raise KeyboardInterrupt("操作被用户中断")
        else:
            # 对于其他信号，退出程序
            import os

            os._exit(0)

    def register_model(self, model):
        """注册模型实例。

        Args:
            model: Faster Whisper 模型实例
        """
        self._model = model

    def cleanup(self):
        """Clean up model resources."""
        if self._model is not None:
            try:
                log_info("Releasing Faster Whisper model resources...")
                del self._model
                self._model = None
                gc.collect()
                log_info("Faster Whisper model resources released")
            except Exception as e:
                log_warning(f"Error releasing model resources: {e}")

    @property
    def has_model(self) -> bool:
        """检查是否有已注册的模型。"""
        return self._model is not None


# ==================== 单例管理 ====================

# 全局单例实例（延迟初始化）
_resource_manager: Optional[ModelResourceManager] = None


def get_resource_manager() -> ModelResourceManager:
    """获取模型资源管理器单例（延迟初始化）。"""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ModelResourceManager()
    return _resource_manager


def reset_resource_manager() -> None:
    """重置模型资源管理器（用于测试）。

    注意：这会清除信号处理器设置，应仅在测试中使用。
    """
    global _resource_manager
    if _resource_manager is not None:
        # 恢复原始信号处理器
        for sig, original_handler in _resource_manager._original_signals.items():
            try:
                signal.signal(sig, original_handler)
            except (ValueError, AttributeError):
                pass
        _resource_manager = None
        ModelResourceManager._instance = None
        ModelResourceManager._initialized = False


@contextmanager
def whisper_model(model_size: str, device: str):
    """Faster Whisper 模型上下文管理器。

    注意：模型已固定为 Large V3，model_size 参数仅用于兼容性。

    Args:
        model_size: 模型大小（已弃用，固定使用 large-v3）
        device: 计算设备 ("cuda" 或 "cpu")

    Yields:
        WhisperModel: Faster Whisper Large V3 模型实例

    Raises:
        ProcessingError: 如果模型不存在或不完整

    Example:
        ```python
        with whisper_model("large-v3", "cpu") as model:
            result = recognition_engine.transcribe(model, audio_path)
        # 模型自动在此处释放
        ```
    """
    from .models.whisper_runtime import load_model

    model = load_model(model_size, device=device)
    get_resource_manager().register_model(model)

    try:
        yield model
    finally:
        get_resource_manager().cleanup()
