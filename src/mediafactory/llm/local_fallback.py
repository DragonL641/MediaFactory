"""本地模型回退模块。

提供轻量级本地翻译模型作为 LLM API 的回退方案。
默认使用 M2M100-418M（3.7GB，100种语言，仅需4GB RAM）。

特性：
- 懒加载：首次使用时才加载模型
- 会话期间保持加载状态
- 翻译完成后释放资源
"""

import gc
from typing import Optional, Tuple

import torch

from ..logging import log_debug, log_error, log_info, log_warning


class LocalModelFallback:
    """本地模型回退，懒加载，翻译会话期间保持。

    用于在 LLM API 翻译失败时提供本地翻译能力。
    默认使用 M2M100-418M 模型，支持 100 种语言。
    """

    DEFAULT_MODEL = "facebook/m2m100_418M"

    # M2M100 支持的语言代码（ISO 639-1）
    # 参考: https://huggingface.co/facebook/m2m100_418M
    M2M100_SUPPORTED_LANGS = {
        "zh", "en", "ja", "ko", "fr", "de", "es", "ru", "it", "pt",
        "nl", "ar", "hi", "vi", "th", "tr", "pl", "uk", "id", "ms",
        "cs", "da", "el", "fi", "hu", "no", "ro", "sk", "sv", "bg",
        "bn", "ca", "hr", "he", "lt", "lv", "sr", "sl", "ta", "te",
        "ml", "mr", "ne", "pa", "si", "sw", "ur", "af", "am", "az",
        "eu", "gl", "ka", "kk", "km", "ky", "lo", "mk", "mn", "my",
        "ps", "sq", "tg", "tk", "uz", "xh", "yo", "zu"
    }

    def __init__(self, device: str = "auto"):
        """初始化本地模型回退。

        Args:
            device: 设备选择 ("auto", "cpu", "cuda", "mps")
        """
        self._device = self._select_device(device)
        self._model = None
        self._tokenizer = None
        self._loaded = False
        self._model_id = self.DEFAULT_MODEL

    def _select_device(self, device: str) -> str:
        """选择运行设备。"""
        if device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
            else:
                return "cpu"
        return device

    @property
    def is_loaded(self) -> bool:
        """检查模型是否已加载。"""
        return self._loaded

    @property
    def device(self) -> str:
        """获取当前设备。"""
        return self._device

    def load(self) -> bool:
        """懒加载模型。

        Returns:
            True 如果加载成功，False 否则
        """
        if self._loaded:
            return True

        log_info(f"[LocalFallback] 开始加载本地翻译模型: {self._model_id}")
        log_info(f"[LocalFallback] 使用设备: {self._device}")

        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            from ..models.model_download import get_models_dir, is_model_complete

            # 检查本地是否存在模型
            local_path = None
            if is_model_complete(self._model_id):
                local_path = str(get_models_dir() / self._model_id)
                log_info(f"[LocalFallback] 使用本地模型: {local_path}")
            else:
                log_info(f"[LocalFallback] 本地模型不存在，尝试从 HuggingFace 加载")

            # 加载 tokenizer
            log_info("[LocalFallback] 加载 tokenizer...")
            if local_path:
                self._tokenizer = AutoTokenizer.from_pretrained(local_path)
            else:
                self._tokenizer = AutoTokenizer.from_pretrained(self._model_id)

            # 加载模型
            log_info("[LocalFallback] 加载模型权重...")
            torch_dtype = torch.float32  # M2M100-418M 使用 float32

            if local_path:
                self._model = AutoModelForSeq2SeqLM.from_pretrained(
                    local_path, torch_dtype=torch_dtype
                )
            else:
                self._model = AutoModelForSeq2SeqLM.from_pretrained(
                    self._model_id, torch_dtype=torch_dtype
                )

            # 移动到目标设备
            if self._device != "cpu":
                log_info(f"[LocalFallback] 移动模型到设备: {self._device}")
                self._model = self._model.to(self._device)

            self._loaded = True
            log_info("[LocalFallback] 本地模型加载成功")
            return True

        except Exception as e:
            log_error(f"[LocalFallback] 模型加载失败: {e}")
            self._loaded = False
            return False

    def translate_single(
        self,
        text: str,
        tgt_lang: str,
        src_lang: Optional[str] = None,
    ) -> str:
        """单句翻译。

        Args:
            text: 待翻译文本
            tgt_lang: 目标语言代码（ISO 639-1）
            src_lang: 源语言代码（可选，默认自动检测）

        Returns:
            翻译结果文本
        """
        if not self._loaded:
            if not self.load():
                log_error("[LocalFallback] 模型未加载，返回原始文本")
                return text

        try:
            # 获取语言代码
            src_code = self._get_lang_code(src_lang) if src_lang else "en"
            tgt_code = self._get_lang_code(tgt_lang)

            if src_code is None:
                log_warning(f"[LocalFallback] 不支持的源语言: {src_lang}，使用 'en'")
                src_code = "en"
            if tgt_code is None:
                log_warning(f"[LocalFallback] 不支持的目标语言: {tgt_lang}，返回原文")
                return text

            log_debug(f"[LocalFallback] 翻译: {src_code} -> {tgt_code}")

            # 设置源语言
            self._tokenizer.src_lang = src_code

            # 编码输入
            inputs = self._tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
            )

            # 移动到相同设备
            inputs = {k: v.to(self._model.device) for k, v in inputs.items()}

            # 生成翻译
            forced_bos_token_id = self._tokenizer.get_lang_id(tgt_code)

            with torch.no_grad():
                translated = self._model.generate(
                    **inputs,
                    max_length=512,
                    forced_bos_token_id=forced_bos_token_id,
                )

            # 解码结果
            translated_text = self._tokenizer.decode(
                translated[0], skip_special_tokens=True
            )

            log_debug(
                f"[LocalFallback] 翻译结果: {translated_text[:80]}..."
                if len(translated_text) > 80
                else f"[LocalFallback] 翻译结果: {translated_text}"
            )

            return translated_text

        except Exception as e:
            log_error(f"[LocalFallback] 翻译失败: {e}")
            return text

    def _get_lang_code(self, lang: str) -> Optional[str]:
        """获取 M2M100 语言代码。

        Args:
            lang: 语言代码（ISO 639-1）

        Returns:
            M2M100 支持的语言代码，如果不支持返回 None
        """
        if not lang:
            return None
        lang_lower = lang.lower()
        return lang_lower if lang_lower in self.M2M100_SUPPORTED_LANGS else None

    def release(self):
        """释放模型资源。

        在翻译会话完成后调用，释放 GPU/CPU 内存。
        """
        if self._model is not None:
            log_info("[LocalFallback] 释放本地模型资源...")

            del self._model
            del self._tokenizer
            self._model = None
            self._tokenizer = None
            self._loaded = False

            # 强制垃圾回收
            gc.collect()

            # 如果使用 CUDA，清理缓存
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            log_info("[LocalFallback] 本地模型资源已释放")

    def __enter__(self):
        """上下文管理器入口。"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出，自动释放资源。"""
        self.release()
        return False
