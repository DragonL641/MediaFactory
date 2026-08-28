"""MediaFactory 模型资源管理。

提供 Whisper 模型上下文管理器，确保加载后正确释放。
"""

import gc
from contextlib import contextmanager


@contextmanager
def whisper_model(model_id: str, device: str):
    """Faster Whisper 模型上下文管理器。

    模型固定为 Large V3，model_id 参数仅用于日志记录。

    Args:
        model_id: 模型 ID（固定使用 Large V3，此参数仅用于日志）
        device: 计算设备 ("cuda" 或 "cpu")

    Yields:
        WhisperModel: Faster Whisper Large V3 模型实例
    """
    from .models.whisper_runtime import load_model
    from .logging import log_info

    model = load_model(device=device)
    log_info(f"Whisper model loaded on {device}")
    try:
        yield model
    finally:
        del model
        gc.collect()
        log_info("Whisper model released")
