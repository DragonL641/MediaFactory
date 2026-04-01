"""本地模型回退模块。

提供本地翻译模型作为 LLM API 的回退方案。
委托给 local_model_manager 进行模型加载和翻译，
避免重复加载模型实例。

特性：
- 委托给 local_model_manager 单例管理模型生命周期
- 自动继承 CUDA/MPS/CPU 设备支持
- 无需维护独立的语言代码表
"""

from ..logging import log_debug, log_error, log_info, log_warning


class LocalModelFallback:
    """本地模型回退，委托给 local_model_manager。

    用于在 LLM API 翻译失败时提供本地翻译能力。
    通过 local_model_manager 获取翻译 callable，避免重复加载模型。
    """

    @staticmethod
    def _extract_translation(result, fallback_text: str) -> str:
        """从翻译模型输出中提取译文，失败返回 fallback_text。"""
        if (
            result
            and isinstance(result, list)
            and len(result) > 0
            and isinstance(result[0], dict)
            and "translation_text" in result[0]
        ):
            translated = result[0]["translation_text"]
            log_debug(
                f"[LocalFallback] 翻译结果: {translated[:80]}..."
                if len(translated) > 80
                else f"[LocalFallback] 翻译结果: {translated}"
            )
            return translated

        log_warning("[LocalFallback] 翻译结果格式异常，返回原文")
        return fallback_text

    def translate_single(
        self, text: str, tgt_lang: str, src_lang: str = "en"
    ) -> str:
        """翻译单条文本。"""
        try:
            from ..models.translation_runtime import get_translation_model

            model_callable = get_translation_model(src_lang, tgt_lang)
            if not model_callable:
                log_warning("[LocalFallback] 本地翻译模型不可用，返回原文")
                return text

            result = model_callable(text, max_length=512, truncation=True)
            return self._extract_translation(result, text)

        except Exception as e:
            log_error(f"[LocalFallback] 翻译失败: {e}")
            return text

    def translate_batch(
        self, texts: list, tgt_lang: str, src_lang: str = "en"
    ) -> list:
        """批量翻译（加载模型一次，逐句翻译）。"""
        from ..models.translation_runtime import get_translation_model

        model_callable = get_translation_model(src_lang, tgt_lang)
        if not model_callable:
            log_warning("[LocalFallback] 本地翻译模型不可用，返回原文")
            return list(texts)

        results = []
        for text in texts:
            try:
                result = model_callable(text, max_length=512, truncation=True)
                results.append(self._extract_translation(result, text))
            except Exception as e:
                log_error(f"[LocalFallback] 翻译失败: {e}")
                results.append(text)
        return results

    def release(self):
        """释放资源（空操作）。

        模型生命周期由 local_model_manager 单例管理，
        此方法保留以兼容上下文管理器协议。
        """
        pass

    def __enter__(self):
        """上下文管理器入口。"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出。"""
        return False
