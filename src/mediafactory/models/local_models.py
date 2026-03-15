"""Unified local model management module for MediaFactory.

This module manages both Whisper and translation models using the unified model registry.
Supports:
- Whisper models for speech recognition
- MADLAD400 translation models with Apache 2.0 license for commercial use
"""

import threading
from typing import Optional, Tuple

import torch

from .model_download import get_models_dir, is_model_complete, is_model_downloaded
from .model_registry import (
    MODEL_REGISTRY,
    ModelType,
    get_display_name,
    get_model_info,
    get_translation_model_info,
    select_best_translation_model,
)
from ..config import get_config_manager
from ..logging import log_debug, log_error, log_info, log_warning


class LocalModelManager:
    """Unified manager for local Whisper and translation models.

    This class provides model discovery, loading, and management using
    the unified model registry. Supports both:
    - Whisper models (speech recognition)
    - Translation models (MADLAD400 with Apache 2.0 license)
    """

    def __init__(self):
        self.config_manager = get_config_manager()
        self.config = self.config_manager.config

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
    ) -> Tuple[Optional[object], bool]:
        """Get model from local storage.

        Args:
            huggingface_id: HuggingFace 模型 ID（如 "google/madlad400-3b-mt"）
            device: Device to load model on ("cpu", "cuda", etc.)
            src_lang: Source language code
            tgt_lang: Target language code

        Returns:
            Tuple of (translation_callable, is_local_flag), or (None, False) if not found
        """
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        # Get model info from registry
        model_info = get_translation_model_info(huggingface_id)
        if model_info is None:
            log_warning(f"Unknown model ID: {huggingface_id}")
            return None, False

        # Try to load from local storage
        local_path = self.get_local_model_path(huggingface_id)
        if not local_path:
            self._log_model_not_found_error(huggingface_id)
            return None, False

        try:
            log_info(f"Loading model {model_info.display_name} from {local_path}")

            # Determine torch dtype based on precision
            torch_dtype = torch.float32
            if model_info.precision == "fp16":
                torch_dtype = torch.float16

            # Load tokenizer and model directly (safetensors format)
            tokenizer = AutoTokenizer.from_pretrained(local_path)
            model = AutoModelForSeq2SeqLM.from_pretrained(
                local_path, torch_dtype=torch_dtype
            )

            # Move model to specified device
            if device == "cuda" and torch.cuda.is_available():
                model = model.to("cuda")
            elif device == "mps" and torch.backends.mps.is_available():
                model = model.to("mps")

            # Create a translation callable
            def translate_callable(
                text: str,
                max_length: int = 512,
                truncation: bool = True,
                **kwargs,
            ):
                """Translation callable compatible with pipeline interface."""
                log_debug(
                    f"[Translation] Input: {text[:80]}..."
                    if len(text) > 80
                    else f"[Translation] Input: {text}"
                )

                # Check if this is an M2M100 model
                is_m2m100 = self._is_m2m100_model(huggingface_id)

                if is_m2m100:
                    # M2M100 翻译方式
                    # 需要设置源语言，并使用 forced_bos_token_id 指定目标语言
                    src_code = self._get_m2m100_lang_code(src_lang) if src_lang else "en"
                    tgt_code = self._get_m2m100_lang_code(tgt_lang) if tgt_lang else "en"

                    if src_code is None:
                        log_warning(f"Unsupported source language for M2M100: {src_lang}, using 'en'")
                        src_code = "en"
                    if tgt_code is None:
                        log_warning(f"Unsupported target language for M2M100: {tgt_lang}, using 'en'")
                        tgt_code = "en"

                    log_debug(f"[Translation] M2M100: {src_code} -> {tgt_code}")

                    # 设置源语言
                    tokenizer.src_lang = src_code

                    # 编码输入
                    inputs = tokenizer(
                        text,
                        return_tensors="pt",
                        truncation=truncation,
                        max_length=max_length,
                    )

                    # Move inputs to same device as model
                    inputs = {k: v.to(model.device) for k, v in inputs.items()}

                    # 生成翻译，使用 forced_bos_token_id 指定目标语言
                    forced_bos_token_id = tokenizer.get_lang_id(tgt_code)
                    gen_kwargs = {
                        "max_length": max_length,
                        "forced_bos_token_id": forced_bos_token_id,
                    }
                else:
                    # MADLAD400 翻译方式
                    # 在输入文本前添加目标语言标签，格式: "<2xx> 原文本"
                    input_text = text
                    if tgt_lang:
                        tgt_token = self._get_target_language_token(
                            huggingface_id, tgt_lang
                        )
                        if tgt_token:
                            input_text = f"{tgt_token} {text}"
                            log_debug(f"[Translation] Target language token: {tgt_token}")

                    inputs = tokenizer(
                        input_text,
                        return_tensors="pt",
                        truncation=truncation,
                        max_length=max_length,
                    )

                    # Move inputs to same device as model
                    inputs = {k: v.to(model.device) for k, v in inputs.items()}

                    # Generate translation
                    gen_kwargs = {"max_length": max_length}

                with torch.no_grad():
                    translated = model.generate(**inputs, **gen_kwargs)

                # Decode and return in pipeline-compatible format
                translated_text = tokenizer.decode(
                    translated[0], skip_special_tokens=True
                )
                log_debug(
                    f"[Translation] Output: {translated_text[:80]}..."
                    if len(translated_text) > 80
                    else f"[Translation] Output: {translated_text}"
                )
                return [{"translation_text": translated_text}]

            log_info(f"Model {model_info.display_name} loaded successfully")
            return translate_callable, True

        except Exception as e:
            log_error(f"Failed to load model {huggingface_id} from {local_path}: {e}")
            return None, False

    def _get_target_language_token(
        self, huggingface_id: str, tgt_lang: str
    ) -> Optional[str]:
        """Get the target language token for a model.

        Args:
            huggingface_id: HuggingFace 模型 ID
            tgt_lang: Target language code

        Returns:
            Language token string, or None if not applicable
        """
        # MADLAD400 使用 ISO 639-1 格式的语言 token: "<2xx>"
        # 参考: https://huggingface.co/google/madlad400-3b-mt
        lang_code_map = {
            "zh": "<2zh>",
            "en": "<2en>",
            "ja": "<2ja>",
            "ko": "<2ko>",
            "fr": "<2fr>",
            "de": "<2de>",
            "es": "<2es>",
            "ru": "<2ru>",
            "it": "<2it>",
            "pt": "<2pt>",
            "nl": "<2nl>",
            "ar": "<2ar>",
            "hi": "<2hi>",
            "vi": "<2vi>",
            "th": "<2th>",
            "tr": "<2tr>",
            "pl": "<2pl>",
            "uk": "<2uk>",
            "id": "<2id>",
            "ms": "<2ms>",
        }
        return lang_code_map.get(tgt_lang.lower())

    def _is_m2m100_model(self, huggingface_id: str) -> bool:
        """Check if the model is an M2M100 variant.

        Args:
            huggingface_id: HuggingFace 模型 ID

        Returns:
            True if the model is M2M100, False otherwise
        """
        return "m2m100" in huggingface_id.lower()

    def _get_m2m100_lang_code(self, lang: str) -> Optional[str]:
        """Get M2M100 language code.

        M2M100 uses ISO 639-1 codes directly.

        Args:
            lang: Language code (e.g., "zh", "en")

        Returns:
            M2M100 language code, or None if not supported
        """
        # M2M100 支持的语言代码（ISO 639-1）
        # 参考: https://huggingface.co/facebook/m2m100_418M
        m2m100_supported = {
            "zh", "en", "ja", "ko", "fr", "de", "es", "ru", "it", "pt",
            "nl", "ar", "hi", "vi", "th", "tr", "pl", "uk", "id", "ms",
            "cs", "da", "el", "fi", "hu", "no", "ro", "sk", "sv", "bg",
            "bn", "ca", "hr", "he", "lt", "lv", "sr", "sl", "ta", "te",
            "ml", "mr", "ne", "pa", "si", "sw", "ur", "af", "am", "az",
            "eu", "gl", "ka", "kk", "km", "ky", "lo", "mk", "mn", "my",
            "ps", "sq", "tg", "tk", "uz", "xh", "yo", "zu"
        }
        lang_lower = lang.lower()
        return lang_lower if lang_lower in m2m100_supported else None

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
        All MADLAD400 models use the same language token format.

        Args:
            lang: Generic language code (e.g., "zh", "en")
            model_type: Model type (not used)

        Returns:
            Model-specific language code
        """
        # MADLAD400 使用统一的语言代码
        return lang


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
