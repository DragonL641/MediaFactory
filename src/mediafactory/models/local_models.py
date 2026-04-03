"""Unified local model management module for MediaFactory.

This module manages both Whisper and translation models using the unified model registry.
Supports:
- Whisper models for speech recognition
- M2M100 translation models with MIT license for commercial use
"""

import gc
import threading
import weakref
from typing import Any, Optional, Tuple

# NOTE: torch is imported lazily inside functions to allow the application
# to start without ML dependencies (they are installed via Setup Wizard)

from .model_download import get_models_dir
from .model_registry import is_model_complete, is_model_downloaded
from .model_registry import (
    MODEL_REGISTRY,
    ModelType,
    get_display_name,
    get_model_info,
    get_translation_model_info,
    select_best_translation_model,
)
from ..config import get_config_manager
from ..logging import log_debug, log_error, log_info, log_warning, log_success


class LocalModelManager:
    """Unified manager for local Whisper and translation models.

    This class provides model discovery, loading, and management using
    the unified model registry. Supports both:
    - Whisper models (speech recognition)
    - Translation models (M2M100 with MIT license)
    """

    def __init__(self):
        self.config_manager = get_config_manager()
        self.config = self.config_manager.config
        # 跟踪已加载的模型，用于卸载时清理
        self._loaded_models: dict[str, tuple[Any, Any]] = {}  # huggingface_id -> (model, tokenizer)
        self._models_lock = threading.Lock()

    def get_model_path(self) -> str:
        """Get the local model storage path.

        Returns:
            The model path read from config.toml's model.local_model_path
        """
        return str(self.config.model.local_model_path)

    def get_local_model_path(self, huggingface_id: str) -> Optional[str]:
        """Get the local path if the model exists locally.

        使用 is_model_complete() 验证模型完整性。

        Args:
            huggingface_id: HuggingFace 模型 ID（如 "Systran/faster-whisper-large-v3"）

        Returns:
            本地模型路径，如果不存在则返回 None
        """
        if huggingface_id is None:
            return None

        # 使用完整性验证
        if not is_model_complete(huggingface_id):
            return None

        # 返回完整路径
        return str(get_models_dir() / huggingface_id)

    def is_model_available_locally(self, model_id: str) -> bool:
        """Check if a model is available locally and complete.

        使用 is_model_complete() 验证模型完整性。

        Args:
            model_id: Model identifier

        Returns:
            True if the model exists locally and is complete, otherwise False
        """
        if model_id is None:
            return False
        return is_model_complete(model_id)

    def get_downloaded_translation_models(self) -> list[str]:
        """从配置文件获取已下载的翻译模型列表。

        Returns:
            已下载的翻译模型 huggingface_id 列表
        """
        # 刷新配置以获取最新状态
        self.config_manager.reload()
        return list(self.config_manager.config.model.available_translation_models)

    def get_downloaded_whisper_models(self) -> list[str]:
        """从配置文件获取已下载的 Whisper 模型列表。

        Returns:
            已下载的 Whisper 模型 huggingface_id 列表
        """
        # 刷新配置以获取最新状态
        self.config_manager.reload()
        return list(self.config_manager.config.model.whisper_models)

    def is_whisper_available(self) -> bool:
        """Check if any Whisper model is available locally.

        Returns:
            True if at least one Whisper model exists
        """
        return len(self.get_downloaded_whisper_models()) > 0

    def has_models(self) -> bool:
        """Check if any models (Whisper or translation) are available.

        Returns:
            True if at least one model exists
        """
        return (
            self.is_whisper_available()
            or len(self.get_downloaded_translation_models()) > 0
        )

    def get_best_available_model(self) -> Optional[str]:
        """Get the best available translation model based on current memory.

        Returns:
            Best model ID, or None if no models are available
        """
        downloaded = self.get_downloaded_translation_models()
        return select_best_translation_model(downloaded)

    def get_model_with_fallback(
        self,
        huggingface_id: str,
        device: str = "cpu",
        src_lang: Optional[str] = None,
        tgt_lang: Optional[str] = None,
        progress: Optional[Any] = None,
    ) -> Tuple[Optional[object], bool]:
        """Get model from local storage.

        Args:
            huggingface_id: HuggingFace 模型 ID（如 "facebook/m2m100_1.2B"）
            device: Device to load model on ("cpu", "cuda", etc.)
            src_lang: Source language code
            tgt_lang: Target language code
            progress: Optional progress callback for reporting loading status

        Returns:
            Tuple of (translation_callable, is_local_flag), or (None, False) if not found
        """
        # 检查已加载的模型是否可复用（避免重复加载）
        with self._models_lock:
            if huggingface_id in self._loaded_models:
                cached_model, cached_tokenizer = self._loaded_models[huggingface_id]
                if cached_model is not None and cached_tokenizer is not None:
                    log_info(f"[LocalModelManager] 模型已加载，直接复用: {huggingface_id}")
                    translate_callable = self._create_translate_callable(
                        cached_model, cached_tokenizer, huggingface_id,
                        src_lang, tgt_lang,
                    )
                    return translate_callable, True

        # Lazy import ML dependencies (not bundled in PyInstaller)
        import torch

        log_info(f"[LocalModelManager] Starting model loading for: {huggingface_id}")
        log_info(f"[LocalModelManager] Device: {device}, src_lang: {src_lang}, tgt_lang: {tgt_lang}")

        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        # Get model info from registry
        model_info = get_translation_model_info(huggingface_id)
        if model_info is None:
            log_warning(f"Unknown model ID: {huggingface_id}")
            return None, False

        log_info(f"[LocalModelManager] Model info: {model_info.display_name}, size: {model_info.model_size_mb / 1024:.1f} GB")

        # Try to load from local storage
        log_info(f"[LocalModelManager] Checking local model path...")
        local_path = self.get_local_model_path(huggingface_id)
        if not local_path:
            log_error(f"[LocalModelManager] Model not found locally: {huggingface_id}")
            self._log_model_not_found_error(huggingface_id)
            return None, False

        log_info(f"[LocalModelManager] Model found at: {local_path}")

        try:
            log_info(f"[LocalModelManager] Loading model {model_info.display_name}...")
            log_info(f"[LocalModelManager] This may take a few minutes for large models...")
            log_debug(f"[LocalModelManager] progress callback: {progress is not None}")

            # Determine torch dtype based on precision
            torch_dtype = torch.float32
            if model_info.precision == "fp16":
                torch_dtype = torch.float16
            log_info(f"[LocalModelManager] Using precision: {model_info.precision}, torch_dtype: {torch_dtype}")

            # Load tokenizer and model directly (safetensors format)
            if progress:
                log_debug("[LocalModelManager] Calling progress.update(6, 'Loading tokenizer...')")
                progress.update(6, "Loading tokenizer...")
            log_info(f"[LocalModelManager] Loading tokenizer...")
            tokenizer = AutoTokenizer.from_pretrained(local_path)
            log_info(f"[LocalModelManager] Tokenizer loaded successfully")

            # Model loading - this is the slow step, provide more frequent updates
            if progress:
                log_debug("[LocalModelManager] Calling progress.update(8, 'Loading model weights...')")
                progress.update(8, "Loading model weights (this may take a few minutes)...")
            log_info(f"[LocalModelManager] Loading model weights (this is the slow step)...")
            log_info(f"[LocalModelManager] Model size: {model_info.model_size_mb / 1024:.1f} GB - please wait...")

            # Heartbeat progress mechanism to keep UI responsive during blocking load
            class HeartbeatProgress:
                """Background thread that sends periodic progress updates during blocking operations."""

                def __init__(self, progress_callback, interval: float = 2.0):
                    self.progress_callback = progress_callback
                    self.interval = interval
                    self._stop_event = threading.Event()
                    self._thread = None
                    self._counter = 0

                def _heartbeat(self):
                    while not self._stop_event.is_set():
                        self._counter += 1
                        if self.progress_callback:
                            # Cycle progress between 8-12% to show activity
                            pct = 8 + (self._counter % 5)
                            elapsed = self._counter * self.interval
                            self.progress_callback.update(
                                pct, f"Loading model weights... ({elapsed:.0f}s elapsed)"
                            )
                        self._stop_event.wait(self.interval)

                def start(self):
                    self._thread = threading.Thread(target=self._heartbeat, daemon=True)
                    self._thread.start()

                def stop(self):
                    self._stop_event.set()
                    if self._thread:
                        self._thread.join(timeout=5.0)  # 增加超时到 5 秒
                        if self._thread.is_alive():
                            log_warning("HeartbeatProgress thread did not stop gracefully within timeout")

            # Start heartbeat before blocking call
            heartbeat = HeartbeatProgress(progress, interval=2.0)
            heartbeat.start()

            import time
            start_time = time.time()
            try:
                model = AutoModelForSeq2SeqLM.from_pretrained(
                    local_path, dtype=torch_dtype
                )
            finally:
                # Always stop heartbeat, even if loading fails
                heartbeat.stop()
            elapsed = time.time() - start_time
            log_info(f"[LocalModelManager] Model weights loaded into memory in {elapsed:.1f} seconds")

            # Update progress after model is loaded
            if progress:
                log_debug("[LocalModelManager] Calling progress.update(10, 'Model weights loaded')")
                progress.update(10, "Model weights loaded into memory")

            # Move model to specified device
            if progress:
                log_debug(f"[LocalModelManager] Calling progress.update(12, 'Moving model to {device}...')")
                progress.update(12, f"Moving model to {device}...")
            log_info(f"[LocalModelManager] Moving model to device: {device}")
            if device == "cuda" and torch.cuda.is_available():
                log_info(f"[LocalModelManager] CUDA available, moving model to GPU...")
                model = model.to("cuda")
                log_info(f"[LocalModelManager] Model moved to CUDA successfully")
            elif device == "mps" and torch.backends.mps.is_available():
                log_info(f"[LocalModelManager] MPS available, moving model to Apple Silicon GPU...")
                model = model.to("mps")
                log_info(f"[LocalModelManager] Model moved to MPS successfully")
            else:
                log_info(f"[LocalModelManager] Using CPU device")

            # 记录已加载的模型，用于卸载
            with self._models_lock:
                self._loaded_models[huggingface_id] = (model, tokenizer)
            log_debug(f"[LocalModelManager] Model tracked for cleanup: {huggingface_id}")

            # 使用预解析语言代码的 callable
            translate_callable = self._create_translate_callable(
                model, tokenizer, huggingface_id, src_lang, tgt_lang,
            )

            if progress:
                progress.update(15, "Model loaded successfully")
            log_info(f"Model {model_info.display_name} loaded successfully")
            return translate_callable, True

        except Exception as e:
            log_error(f"Failed to load model {huggingface_id} from {local_path}: {e}")
            return None, False

    def _get_lang_code(self, lang: str) -> Optional[str]:
        """Get language code for M2M100.

        M2M100 uses ISO 639-1 codes directly.

        Args:
            lang: Language code (e.g., "zh", "en")

        Returns:
            M2M100 language code, or None if not supported
        """
        # M2M100 支持的语言代码（ISO 639-1）
        # 参考: https://huggingface.co/facebook/m2m100_1.2B
        m2m100_supported = {
            "zh", "en", "ja", "ko", "fr", "de", "es", "ru", "it", "pt",
            "nl", "ar", "hi", "vi", "th", "tr", "pl", "uk", "id", "ms",
            "cs", "da", "el", "fi", "hu", "no", "ro", "sk", "sv", "bg",
            "bn", "ca", "hr", "he", "lt", "lv", "sr", "sl", "ta", "te",
            "ml", "mr", "ne", "pa", "si", "sw", "ur", "af", "am", "az",
            "eu", "gl", "ka", "kk", "km", "ky", "lo", "mk", "mn", "my",
            "ps", "sq", "tg", "tk", "uz", "xh", "yo", "zu"
        }
        # 提取主语言代码，忽略 locale 标签（如 zh-CN → zh）
        primary = lang.lower().split("-")[0].split("_")[0]
        return primary if primary in m2m100_supported else None

    def _log_model_not_found_error(self, huggingface_id: str) -> None:
        """Log error when model is not found locally.

        Args:
            huggingface_id: 没找到的 HuggingFace 模型 ID
        """
        model_info = get_translation_model_info(huggingface_id)
        from ..config import get_app_root_dir

        models_dir = str(get_app_root_dir() / "models")

        if model_info:
            error_msg = (
                f"Model '{model_info.display_name}' not found locally. "
                f"Please download it to {models_dir}. "
                f"Run: python scripts/utils/download_model.py {huggingface_id}"
            )
        else:
            error_msg = (
                f"Model '{huggingface_id}' not found locally and is not in the registry. "
                f"Please download it to {models_dir}."
            )
        log_error(error_msg)

    def get_lang_code(self, lang: str, model_type: str) -> str:
        """Map generic language codes to model-specific language codes.

        This method is kept for backward compatibility.
        M2M100 uses ISO 639-1 language codes directly.

        Args:
            lang: Generic language code (e.g., "zh", "en")
            model_type: Model type (not used)

        Returns:
            Model-specific language code
        """
        return lang

    def _create_translate_callable(
        self,
        model,
        tokenizer,
        huggingface_id: str,
        src_lang: Optional[str],
        tgt_lang: Optional[str],
    ):
        """创建翻译 callable，复用已加载的模型和 tokenizer。

        语言代码在创建时解析一次，避免每次翻译调用时重复解析。

        """
        import torch

        # 创建时预解析语言代码
        src_code = self._get_lang_code(src_lang) if src_lang else "en"
        if src_code is None:
            log_warning(f"Unsupported source language for M2M100: {src_lang}, using 'en'")
            src_code = "en"
        tgt_code = self._get_lang_code(tgt_lang) if tgt_lang else "en"
        if tgt_code is None:
            log_warning(f"Unsupported target language for M2M100: {tgt_lang}, using 'en'")
            tgt_code = "en"

        # 使用弱引用避免循环引用
        model_ref = weakref.ref(model)
        tokenizer_ref = weakref.ref(tokenizer)
        # 闭包捕获预解析的值
        _src_code = src_code
        _tgt_code = tgt_code

        forced_bos_token_id = tokenizer.get_lang_id(tgt_code)

        def translate_callable(
            text,
            max_length: int = 512,
            truncation: bool = True,
            **kwargs,
        ):
            """翻译 callable，支持单条和批量输入。

            Args:
                text: 单条字符串或字符串列表
                max_length: 最大序列长度
                truncation: 是否截断

            Returns:
                单条时返回 [{"translation_text": ...}]，
                批量时返回 [{"translation_text": ...}, ...]
            """
            m = model_ref()
            t = tokenizer_ref()
            if m is None or t is None:
                raise RuntimeError(
                    f"Translation model '{huggingface_id}' has been released. "
                    "Please reload the model before translating."
                )

            # 判断单条还是批量
            is_batch = isinstance(text, list)
            texts = text if is_batch else [text]

            log_debug(
                f"[Translation] Batch input: {len(texts)} sentence(s), "
                f"M2M100: {_src_code} -> {_tgt_code}"
            )

            t.src_lang = _src_code
            inputs = t(
                texts,
                return_tensors="pt",
                truncation=truncation,
                max_length=max_length,
                padding=True,
            )
            inputs = {k: v.to(m.device) for k, v in inputs.items()}

            gen_kwargs = {
                "max_length": max_length,
                "forced_bos_token_id": forced_bos_token_id,
            }

            with torch.no_grad():
                translated = m.generate(**inputs, **gen_kwargs)

            decoded = t.batch_decode(translated, skip_special_tokens=True)

            log_debug(
                f"[Translation] Batch output: {len(decoded)} result(s)"
            )

            results = [{"translation_text": d} for d in decoded]

            # 单条输入保持原有返回格式
            if not is_batch:
                return results[:1]
            return results

        return translate_callable

    def unload_translation_model(self, huggingface_id: str) -> bool:
        """卸载指定的翻译模型以释放内存。

        Args:
            huggingface_id: HuggingFace 模型 ID（如 "facebook/m2m100_1.2B"）

        Returns:
            True 如果模型成功卸载，False 如果模型未加载
        """
        # Lazy import ML dependencies
        import torch

        with self._models_lock:
            if huggingface_id not in self._loaded_models:
                log_debug(f"[LocalModelManager] Model not loaded, nothing to unload: {huggingface_id}")
                return False

            model, tokenizer = self._loaded_models.pop(huggingface_id)
            log_info(f"[LocalModelManager] Unloading model: {huggingface_id}")

            # 删除模型和 tokenizer 引用
            del model
            del tokenizer

        # 触发垃圾回收
        gc.collect()
        log_info("[LocalModelManager] gc.collect() completed")

        # 清理 CUDA 缓存
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            log_info("[LocalModelManager] torch.cuda.empty_cache() completed")

        log_info(f"[LocalModelManager] Model unloaded successfully: {huggingface_id}")
        return True

    def unload_all_translation_models(self) -> int:
        """卸载所有已加载的翻译模型。

        Returns:
            卸载的模型数量
        """
        count = 0
        with self._models_lock:
            model_ids = list(self._loaded_models.keys())

        for model_id in model_ids:
            if self.unload_translation_model(model_id):
                count += 1

        return count

    def cleanup(self) -> None:
        """清理所有资源（实现 ResourceCleanupProtocol）。"""
        self.unload_all_translation_models()


# ==================== 单例管理 ====================

# 全局实例和锁
_local_model_manager_instance: Optional[LocalModelManager] = None
_local_model_manager_lock = threading.Lock()


def get_local_model_manager() -> LocalModelManager:
    """获取全局本地模型管理器实例（线程安全）"""
    global _local_model_manager_instance
    if _local_model_manager_instance is None:
        with _local_model_manager_lock:
            if _local_model_manager_instance is None:
                _local_model_manager_instance = LocalModelManager()
    return _local_model_manager_instance


def reset_local_model_manager() -> None:
    """重置全局本地模型管理器实例（用于测试）"""
    global _local_model_manager_instance
    with _local_model_manager_lock:
        _local_model_manager_instance = None


# 向后兼容：保留原模块级变量，但使用延迟初始化
# 注意：这是一个属性访问代理，实际实例通过 get_local_model_manager() 获取
class _LocalModelManagerProxy:
    """代理类，用于向后兼容模块级 local_model_manager 变量"""

    def __getattr__(self, name):
        return getattr(get_local_model_manager(), name)

    def __setattr__(self, name, value):
        return setattr(get_local_model_manager(), name, value)


local_model_manager = _LocalModelManagerProxy()
