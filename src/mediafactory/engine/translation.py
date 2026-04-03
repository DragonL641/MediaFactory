"""翻译引擎模块

统一接口，内部实现本地翻译和 LLM 翻译。
"""

import copy
import threading
from typing import Dict, List, Any, Optional, TYPE_CHECKING

from ..logging import (
    log_warning,
    log_debug,
    log_info,
    log_error,
    log_step,
    log_language_detection,
)
from ..exceptions import ProcessingError, OperationCancelledError
from ..core.progress_protocol import ProgressCallback, NO_OP_PROGRESS
from ..core.exception_wrapper import wrap_exceptions, convert_exception
from ..utils.resources import get_language_name
from ..i18n import t

if TYPE_CHECKING:
    from ..llm.base import TranslationBackend


# =============================================================================
# 翻译引擎常量（从 constants.py 移入）
# =============================================================================


class TranslationConstants:
    """翻译引擎常量。"""

    DEFAULT_MAX_LENGTH = 512  # 翻译模型最大序列长度
    ENABLE_TRUNCATION = True  # 启用长序列截断
    SEGMENT_NUMBER_OFFSET = 1  # 分段号从 1 开始
    BATCH_SIZE = 8  # 本地翻译批量大小


class TranslationEngine:
    """翻译引擎，支持本地模型和 LLM API"""

    def __init__(
        self,
        use_local_models_only: bool = False,
        model_type: Optional[str] = None,
        device: str = "auto",
        llm_backend: Optional["TranslationBackend"] = None,
        use_llm_backend: bool = False,
    ):
        self.use_local_models_only = use_local_models_only
        self.model_type = model_type
        # 自动检测设备
        if device == "auto":
            from ..models.whisper_runtime import select_device
            self.device = select_device()
        else:
            self.device = device
        log_info(f"TranslationEngine initialized with device={self.device}")
        self.llm_backend = llm_backend
        self.use_llm_backend = use_llm_backend and llm_backend is not None

        self._use_llm = (
            self.use_llm_backend
            and not self.use_local_models_only
            and self.llm_backend
            and self.llm_backend.is_available
        )
        self._language_detector = None
        self._detector_lock = threading.Lock()

    def translate(
        self,
        result: Dict[str, Any],
        src_lang: Optional[str],
        tgt_lang: str,
        progress: Optional[ProgressCallback] = None,
        detection_context: str = "Translation",
    ) -> Dict[str, Any]:
        """翻译转录片段"""
        if progress is None:
            progress = NO_OP_PROGRESS

        try:
            with wrap_exceptions(
                context={
                    "use_llm": self._use_llm,
                    "model_type": self.model_type,
                    "src_lang": src_lang,
                    "tgt_lang": tgt_lang,
                },
                operation="translation",
            ):
                # 语言检测
                detection_result = self._detect_source_language(
                    result, src_lang, detection_context
                )
                actual_src_lang = detection_result.primary_language

                if not actual_src_lang:
                    log_warning(
                        t("error.sourceLanguageNotDetected")
                    )
                    return result

                if actual_src_lang == tgt_lang:
                    log_debug(
                        "Source and target languages are the same, skipping translation"
                    )
                    return result

                # 选择翻译方式
                if self._use_llm:
                    try:
                        return self._translate_with_llm(
                            result, actual_src_lang, tgt_lang, progress
                        )
                    except OperationCancelledError:
                        raise
                    except ProcessingError as e:
                        log_warning(
                            f"LLM translation failed ({e.message}), "
                            f"falling back to local model"
                        )
                    except Exception as e:
                        log_warning(
                            f"LLM translation failed ({e}), "
                            f"falling back to local model"
                        )

                return self._translate_with_local(
                    result, actual_src_lang, tgt_lang, progress
                )

        except ProcessingError:
            raise
        except OperationCancelledError:
            raise
        except Exception as e:
            error_msg = str(e).lower()
            engine_name = "LLM" if self._use_llm else "Local"

            if self._use_llm and (
                "api" in error_msg or "key" in error_msg or "auth" in error_msg
            ):
                backend_name = (
                    type(self.llm_backend).__name__ if self.llm_backend else "unknown"
                )
                raise ProcessingError(
                    message=f"LLM API translation failed: {backend_name}",
                    context={
                        "engine": engine_name,
                        "backend": backend_name,
                        "src_lang": src_lang,
                        "tgt_lang": tgt_lang,
                        "error": str(e),
                    },
                ) from e
            else:
                raise convert_exception(
                    e,
                    context={
                        "engine": engine_name,
                        "src_lang": src_lang,
                        "tgt_lang": tgt_lang,
                    },
                ) from e

    @property
    def engine_type(self) -> str:
        """获取当前引擎类型"""
        return "LLM" if self._use_llm else "Local"

    # ==================== 语言检测 ====================

    def _detect_source_language(
        self, result: Dict[str, Any], src_lang: Optional[str], context: str
    ):
        """检测源语言"""
        if self._language_detector is None:
            with self._detector_lock:
                if self._language_detector is None:
                    from ..utils.language_detector import LanguageDetector
                    from ..utils.resources import LANGUAGE_MAP

                    self._language_detector = LanguageDetector(LANGUAGE_MAP)

        segments = result.get("segments", [])

        text_content = None
        if segments and not result.get("language"):
            texts = [seg.get("text", "") for seg in segments if seg.get("text")]
            if texts:
                text_content = " ".join(texts)

        detection_result = self._language_detector.detect(
            result=result,
            text=text_content,
            specified_lang=src_lang,
            segments=segments if segments else None,
        )

        log_language_detection(detection_result, context)
        return detection_result

    # ==================== 本地翻译 ====================

    def _translate_with_local(
        self,
        result: Dict[str, Any],
        src_lang: str,
        tgt_lang: str,
        progress: ProgressCallback,
    ) -> Dict[str, Any]:
        """使用本地模型翻译"""
        from ..models.local_models import local_model_manager
        from ..models.translation_runtime import get_translation_model

        log_step(
            f"Translating from {get_language_name(src_lang)} to {get_language_name(tgt_lang)} using local model..."
        )
        log_info(f"[TranslationEngine] Using device: {self.device}")
        log_info(f"[TranslationEngine] Model type: {self.model_type}")
        log_debug(f"[TranslationEngine] progress callback: {progress is not None}, type: {type(progress).__name__}")

        # 加载模型
        log_info(
            f"[TranslationEngine] Loading translation model for {src_lang} -> {tgt_lang}..."
        )
        log_info(f"[TranslationEngine] This may take a while for large models (e.g., M2M100-1.2B)")
        log_debug(f"[TranslationEngine] Calling progress.update(5, 'Loading translation model...')")
        progress.update(5, t("progress.loadingTranslationModel"))

        model_callable = get_translation_model(
            src_lang, tgt_lang, device=self.device, progress=progress
        )

        if not model_callable:
            raise ProcessingError(
                message=f"Translation model loading failed for {get_language_name(src_lang)} -> {get_language_name(tgt_lang)}",
                context={
                    "model_type": self.model_type,
                    "src_lang": src_lang,
                    "tgt_lang": tgt_lang,
                    "suggestion": "Please download the translation model",
                },
            )

        log_info("[TranslationEngine] Translation model loaded successfully")
        progress.update(15, t("progress.translationModelLoaded"))

        # 执行翻译
        segments = result.get("segments", [])
        translated_segments = self._local_context_aware_translation(
            segments, src_lang, tgt_lang, model_callable, progress
        )

        self._validate_translation_result(segments, translated_segments)

        translated_result = result.copy()
        translated_result["segments"] = translated_segments
        return translated_result

    def _local_context_aware_translation(
        self,
        segments: List[Dict[str, Any]],
        src_lang: str,
        tgt_lang: str,
        model_callable: Any,
        progress: ProgressCallback,
    ) -> List[Dict[str, Any]]:
        """本地模型批量翻译"""
        from ..models.local_models import local_model_manager

        if not segments:
            return segments

        total_segments = len(segments)

        src_code = local_model_manager.get_lang_code(src_lang, self.model_type)
        tgt_code = local_model_manager.get_lang_code(tgt_lang, self.model_type)

        log_debug(f"[LocalTranslation] src_lang={src_lang} -> src_code={src_code}")
        log_debug(f"[LocalTranslation] tgt_lang={tgt_lang} -> tgt_code={tgt_code}")
        log_debug(
            f"[LocalTranslation] Batch mode: size={TranslationConstants.BATCH_SIZE}, "
            f"total={total_segments} segments"
        )

        # 分批索引：记录每个 batch 对应的 segment 原始索引
        translated_segments = [None] * total_segments
        batch_size = TranslationConstants.BATCH_SIZE

        batch_start = 0
        while batch_start < total_segments:
            if progress.is_cancelled():
                raise OperationCancelledError(
                    message=t("error.translationCancelled"),
                    context={"model_type": self.model_type, "segment_index": batch_start},
                )

            batch_end = min(batch_start + batch_size, total_segments)

            # 收集当前 batch 的非空文本及其索引
            batch_indices = []
            batch_texts = []
            for idx in range(batch_start, batch_end):
                text = segments[idx]["text"].strip()
                if text:
                    batch_indices.append(idx)
                    batch_texts.append(text)

            # 批量翻译非空文本
            if batch_texts:
                progress.update(
                    ((batch_end) / total_segments) * 100,
                    t(
                        "progress.translatingSegment",
                        current=batch_end,
                        total=total_segments,
                    ),
                )

                translated_texts = self._perform_batch_translation(
                    batch_texts, src_code, tgt_code, model_callable
                )

                for j, idx in enumerate(batch_indices):
                    new_segment = copy.deepcopy(segments[idx])
                    new_segment["original_text"] = batch_texts[j]
                    new_segment["text"] = translated_texts[j]
                    translated_segments[idx] = new_segment

            # 空文本直接复制
            for idx in range(batch_start, batch_end):
                if translated_segments[idx] is None:
                    translated_segments[idx] = copy.deepcopy(segments[idx])

            batch_start = batch_end

        progress.update(100.0, t("progress.completed"))
        return translated_segments

    def _perform_batch_translation(
        self,
        texts: List[str],
        src_code: str,
        tgt_code: str,
        model_callable: Any,
    ) -> List[str]:
        """批量翻译，失败时回退逐句翻译"""
        try:
            translations = model_callable(
                texts,
                max_length=TranslationConstants.DEFAULT_MAX_LENGTH,
                truncation=TranslationConstants.ENABLE_TRUNCATION,
            )
            if (
                translations
                and isinstance(translations, list)
                and len(translations) == len(texts)
                and all(
                    isinstance(t, dict) and "translation_text" in t
                    for t in translations
                )
            ):
                return [t["translation_text"] for t in translations]

            # 结果格式不符，回退逐句
            log_warning(
                "Batch translation returned unexpected format, "
                "falling back to per-sentence"
            )
            return self._fallback_per_sentence(
                texts, src_code, tgt_code, model_callable
            )
        except Exception as batch_err:
            # 批量失败，逐句重试
            log_warning(
                f"Batch translation failed ({batch_err}), "
                f"falling back to per-sentence"
            )
            return self._fallback_per_sentence(
                texts, src_code, tgt_code, model_callable
            )

    def _fallback_per_sentence(
        self,
        texts: List[str],
        src_code: str,
        tgt_code: str,
        model_callable: Any,
    ) -> List[str]:
        """逐句翻译回退"""
        results = []
        for text in texts:
            results.append(
                self._perform_multilingual_translation(
                    text, src_code, tgt_code, model_callable
                )
            )
        return results

    def _perform_multilingual_translation(
        self, text: str, src_code: str, tgt_code: str, model_callable: Any
    ) -> str:
        """执行单条多语言翻译"""
        try:
            translation = model_callable(
                text,
                max_length=TranslationConstants.DEFAULT_MAX_LENGTH,
                truncation=TranslationConstants.ENABLE_TRUNCATION,
            )
            if (
                translation
                and isinstance(translation, list)
                and len(translation) > 0
                and isinstance(translation[0], dict)
                and "translation_text" in translation[0]
            ):
                return translation[0]["translation_text"]

            log_warning(f"Segment translation result is empty: '{text[:50]}...'")
            log_warning("Translation model may not support this language pair")
            return text
        except ProcessingError:
            raise
        except Exception as e:
            log_error(f"Error translating segment: {e}")
            log_info("Try remote LLM translation instead")
            return text

    def _validate_translation_result(
        self,
        original_segments: List[Dict[str, Any]],
        translated_segments: List[Dict[str, Any]],
    ) -> None:
        """验证翻译结果"""
        if len(original_segments) > 0:
            first_orig = original_segments[0].get("text", "").strip()
            first_trans = translated_segments[0].get("text", "").strip()
            if first_orig == first_trans and len(first_orig) > 0:
                log_warning("Translation may have failed (output matches input)")
                log_info(
                    "Please check if the translation model is downloaded correctly"
                )

    # ==================== LLM 翻译 ====================

    def _translate_with_llm(
        self,
        result: Dict[str, Any],
        src_lang: str,
        tgt_lang: str,
        progress: ProgressCallback,
    ) -> Dict[str, Any]:
        """使用 LLM API 翻译（简化版）

        降级逻辑在 OpenAICompatibleBackend 内部处理：
        批量 → 纠正 → 分批 → 逐句 → 本地模型
        """
        from ..llm import TranslationRequest

        backend_type = type(self.llm_backend).__name__
        model_name = self.llm_backend.get_model_name

        log_step(
            f"Using {backend_type} ({model_name}) API to translate from "
            f"{get_language_name(src_lang)} to {get_language_name(tgt_lang)}..."
        )

        segments = result.get("segments", [])
        texts = [seg.get("text", "") for seg in segments]

        cancelled_callback = lambda: progress.is_cancelled() if progress else False

        request = TranslationRequest(
            text=texts,
            src_lang=src_lang,
            tgt_lang=tgt_lang,
            cancelled_callback=cancelled_callback,
            progress_callback=progress,
        )

        log_debug(
            f"[LLM Translation] Sending request: {len(texts)} segments, "
            f"src={src_lang}, tgt={tgt_lang}"
        )

        log_step("Calling LLM API...")
        translation_result = self.llm_backend.translate(request)

        log_debug(
            f"[LLM Translation] API response: success={translation_result.success}, "
            f"backend_used={translation_result.backend_used}"
        )

        if not translation_result.success:
            log_error(f"Error message: {translation_result.error_message}")
            raise ProcessingError(
                message=f"LLM translation failed: {backend_type}",
                context={
                    "backend": backend_type,
                    "model": model_name,
                    "src_lang": src_lang,
                    "tgt_lang": tgt_lang,
                    "details": translation_result.error_message,
                    "suggestion": f"Check {backend_type} configuration or try again later",
                },
            )

        # 合并结果到 segments
        translated_segments = self._merge_translation_result(
            segments, translation_result.translated_text
        )

        log_info(f"Translation completed: {len(translated_segments)} segments")

        translated_result = result.copy()
        translated_result["segments"] = translated_segments
        return translated_result

    def _merge_translation_result(
        self,
        segments: List[Dict[str, Any]],
        translated_text,
    ) -> List[Dict[str, Any]]:
        """将翻译结果合并到 segments。

        Args:
            segments: 原始 segments 列表
            translated_text: 翻译结果（字符串或列表）

        Returns:
            合并后的 segments 列表
        """
        translated_segments = []

        if isinstance(translated_text, str):
            # 单个字符串，只更新第一个 segment
            for i, seg in enumerate(segments):
                new_seg = copy.deepcopy(seg)
                new_seg["original_text"] = seg.get("text", "")
                if i == 0:
                    new_seg["text"] = translated_text
                translated_segments.append(new_seg)
        elif isinstance(translated_text, list):
            # 列表，按索引更新
            for i, seg in enumerate(segments):
                new_seg = copy.deepcopy(seg)
                new_seg["original_text"] = seg.get("text", "")
                if i < len(translated_text):
                    new_seg["text"] = translated_text[i]
                translated_segments.append(new_seg)
        else:
            # 未知类型，保留原文
            translated_segments = [copy.deepcopy(seg) for seg in segments]

        return translated_segments

    def _test_api_connection(self) -> None:
        """测试 LLM API 连接"""
        log_step("Testing LLM API connection...")
        test_result = self.llm_backend.test_connection()

        log_debug(
            f"[LLM] Connection test: success={test_result.get('success')}, "
            f"message={test_result.get('message', 'N/A')}"
        )

        if not test_result.get("success"):
            error_msg = test_result.get("message", "Unknown error")
            backend_type = type(self.llm_backend).__name__
            log_error(f"Connection test failed: {error_msg}")

            error_lower = error_msg.lower()
            if "api key" in error_lower or "auth" in error_lower:
                suggestion = f"Check {backend_type} API key in config.toml"
            elif "connection" in error_lower or "network" in error_lower:
                suggestion = "Check internet connection and try again"
            else:
                suggestion = f"Check {backend_type} configuration in config.toml"

            raise ProcessingError(
                message=f"API connection test failed: {backend_type}",
                context={
                    "backend": backend_type,
                    "details": error_msg,
                    "suggestion": suggestion,
                },
            )

        log_info("API connection test successful")

    # ==================== 资源清理 ====================

    def cleanup(self) -> None:
        """清理翻译引擎持有的所有资源。

        实现 ResourceCleanupProtocol 接口。
        应该在引擎不再使用时调用，以释放内存和连接。
        """
        import gc

        log_info("[TranslationEngine] Starting cleanup...")

        # 1. 清理语言检测器
        if self._language_detector is not None:
            log_debug("[TranslationEngine] Releasing language detector")
            self._language_detector = None

        # 2. 清理 LLM 后端
        if self.llm_backend is not None:
            if hasattr(self.llm_backend, "cleanup"):
                try:
                    log_debug("[TranslationEngine] Calling llm_backend.cleanup()")
                    self.llm_backend.cleanup()
                except Exception as e:
                    log_warning(f"[TranslationEngine] Error cleaning up LLM backend: {e}")
            self.llm_backend = None

        # 3. 触发垃圾回收
        gc.collect()
        log_debug("[TranslationEngine] gc.collect() completed")

        log_info("[TranslationEngine] Cleanup completed")
