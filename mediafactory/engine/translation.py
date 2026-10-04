"""翻译引擎模块

统一接口，通过 LLM API 后端翻译。
"""

import threading
from typing import TYPE_CHECKING, Any, Optional

from ..core.exception_wrapper import convert_exception, wrap_exceptions
from ..core.progress_protocol import NO_OP_PROGRESS, ProgressCallback
from ..exceptions import OperationCancelledError, ProcessingError
from ..i18n import t
from ..logging import (
    log_debug,
    log_error,
    log_info,
    log_language_detection,
    log_step,
    log_warning,
)
from ..utils.resources import get_language_name

if TYPE_CHECKING:
    from ..llm.base import TranslationBackend


class TranslationEngine:
    """翻译引擎，通过 LLM API 翻译"""

    def __init__(
        self,
        llm_backend: Optional["TranslationBackend"] = None,
        use_llm_backend: bool = False,
    ):
        self.llm_backend = llm_backend
        self._use_llm = (
            use_llm_backend and llm_backend is not None and llm_backend.is_available
        )
        self._language_detector = None
        self._detector_lock = threading.Lock()

    def translate(
        self,
        result: dict[str, Any],
        src_lang: str | None,
        tgt_lang: str,
        progress: ProgressCallback | None = None,
        detection_context: str = "Translation",
    ) -> dict[str, Any]:
        """翻译转录片段"""
        if progress is None:
            progress = NO_OP_PROGRESS

        try:
            with wrap_exceptions(
                context={
                    "use_llm": self._use_llm,
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
                    log_warning(t("error.sourceLanguageNotDetected"))
                    return result

                if actual_src_lang == tgt_lang:
                    log_debug(
                        "Source and target languages are the same, skipping translation"
                    )
                    return result

                if not self._use_llm:
                    raise ProcessingError(
                        message="LLM translation backend is not configured. "
                        "Please configure an LLM preset in Settings.",
                        context={
                            "src_lang": actual_src_lang,
                            "tgt_lang": tgt_lang,
                        },
                    )

                return self._translate_with_llm(
                    result, actual_src_lang, tgt_lang, progress
                )

        except ProcessingError:
            raise
        except OperationCancelledError:
            raise
        except Exception as e:
            error_msg = str(e).lower()

            if "api" in error_msg or "key" in error_msg or "auth" in error_msg:
                backend_name = (
                    type(self.llm_backend).__name__ if self.llm_backend else "unknown"
                )
                raise ProcessingError(
                    message=f"LLM API translation failed: {backend_name}",
                    context={
                        "engine": "LLM",
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
                        "engine": "LLM",
                        "src_lang": src_lang,
                        "tgt_lang": tgt_lang,
                    },
                ) from e

    # ==================== 语言检测 ====================

    def _detect_source_language(
        self, result: dict[str, Any], src_lang: str | None, context: str
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

    # ==================== LLM 翻译 ====================

    def _translate_with_llm(
        self,
        result: dict[str, Any],
        src_lang: str,
        tgt_lang: str,
        progress: ProgressCallback,
    ) -> dict[str, Any]:
        """使用 LLM API 翻译

        降级逻辑在 OpenAICompatibleBackend 内部处理：
        批量 → 验证失败二分递归 → contentFilter 递归二分 → 失败句保留原文
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

        def cancelled_callback() -> bool:
            return progress.is_cancelled() if progress else False

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
        segments: list[dict[str, Any]],
        translated_text,
    ) -> list[dict[str, Any]]:
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
            log_warning(
                f"[TranslationEngine] 翻译结果为单个字符串，"
                f"只有第 1/{len(segments)} 段被更新"
            )
            for i, seg in enumerate(segments):
                new_seg = seg.copy()
                new_seg["original_text"] = seg.get("text", "")
                if i == 0:
                    new_seg["text"] = translated_text
                translated_segments.append(new_seg)
        elif isinstance(translated_text, list):
            if len(translated_text) != len(segments):
                log_warning(
                    f"[TranslationEngine] 翻译结果数量({len(translated_text)})"
                    f"与段落数量({len(segments)})不匹配"
                )
            for i, seg in enumerate(segments):
                new_seg = seg.copy()
                new_seg["original_text"] = seg.get("text", "")
                if i < len(translated_text):
                    new_seg["text"] = translated_text[i]
                else:
                    new_seg["text"] = ""
                translated_segments.append(new_seg)
        else:
            log_warning(
                f"[TranslationEngine] 翻译结果类型异常: {type(translated_text).__name__}"
            )
            translated_segments = [seg.copy() for seg in segments]

        return translated_segments

    # ==================== 资源清理 ====================

    def cleanup(self) -> None:
        """清理翻译引擎持有的所有资源。

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
                    log_warning(
                        f"[TranslationEngine] Error cleaning up LLM backend: {e}"
                    )
            self.llm_backend = None

        # 3. 触发垃圾回收
        gc.collect()
        log_debug("[TranslationEngine] gc.collect() completed")

        log_info("[TranslationEngine] Cleanup completed")
