"""翻译引擎模块

统一接口，通过 LLM API 后端翻译。
"""

import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from ..constants import OLLAMA_BASE_URL
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


@dataclass
class TranslationOutcome:
    """translate_texts 的输出：译文与四计数统计。"""

    translations: list[str]
    stats: dict[str, int]


class TranslationEngine:
    """翻译引擎，通过 LLM API 翻译"""

    def __init__(
        self,
        llm_backend: Optional["TranslationBackend"] = None,
        use_llm_backend: bool = False,
        user_terms: dict[str, str] | None = None,
        fallback_model: str | None = None,
    ):
        self.llm_backend = llm_backend
        self._use_llm = (
            use_llm_backend and llm_backend is not None and llm_backend.is_available
        )
        self.user_terms = user_terms
        self._language_detector = None
        self._detector_lock = threading.Lock()
        self._fallback_model_name = fallback_model
        self._fallback_backend = self._build_fallback_backend(fallback_model)

    # ==================== 本地兜底 ====================

    def _primary_is_ollama(self) -> bool:
        base_url = getattr(self.llm_backend, "_base_url", "") or ""
        return base_url.startswith(OLLAMA_BASE_URL)

    def _build_fallback_backend(self, fallback_model: str | None):
        """探测 Ollama 并构建兜底 backend；条件不满足返回 None。

        单向约束：主渠道本身就是 Ollama 时不构建（本地→本地无意义）。
        探测失败（服务未运行/模型未拉取）静默降级为无兜底，任务照常。
        """
        if not fallback_model:
            return None
        if self._primary_is_ollama():
            return None
        try:
            from ..llm.ollama_client import get_ollama_client
            from ..llm.openai_compatible_backend import OpenAICompatibleBackend

            client = get_ollama_client()
            if not (
                client.is_available_sync()
                and client.is_model_installed_sync(fallback_model)
            ):
                log_info(
                    "[TranslationEngine] Local fallback unavailable "
                    f"(Ollama down or model missing): {fallback_model}"
                )
                return None
            log_info(f"[TranslationEngine] Local fallback ready: {fallback_model}")
            return OpenAICompatibleBackend(
                base_url=f"{OLLAMA_BASE_URL}/v1", model=fallback_model
            )
        except Exception as e:
            log_warning(f"[TranslationEngine] Fallback probe failed: {e}")
            return None

    def _unload_local_model(self, model: str | None) -> None:
        """翻译步骤结束即卸载用过的本地模型（fire-and-forget，异常吞掉）。"""
        if not model:
            return
        try:
            from ..llm.ollama_client import get_ollama_client

            get_ollama_client().unload_model_sync(model)
        except Exception as e:
            log_debug(f"[TranslationEngine] Unload failed (ignored): {e}")

    def translate_texts(
        self,
        texts: list[str],
        src_lang: str,
        tgt_lang: str,
        progress: ProgressCallback | None = None,
    ) -> TranslationOutcome:
        """直翻一组文本（无 segments 语义），含兜底编排与统计。

        编排：主链 translate_detailed → 失败句转投兜底 backend（共享
        TermDict 保持术语一致）→ 合并 → 四计数；finally 里卸载本次
        用过的本地模型（随用随载由 Ollama 原生保证）。
        """
        from ..llm import TranslationRequest

        def cancelled_callback() -> bool:
            return progress.is_cancelled() if progress else False

        request = TranslationRequest(
            text=texts,
            src_lang=src_lang,
            tgt_lang=tgt_lang,
            cancelled_callback=cancelled_callback,
            progress_callback=progress,
            user_terms=self.user_terms,
        )

        used_local_model: str | None = (
            self.llm_backend.get_model_name if self._primary_is_ollama() else None
        )

        try:
            if hasattr(self.llm_backend, "translate_detailed"):
                detailed = self.llm_backend.translate_detailed(request)
                primary_text = detailed.result.translated_text
                translations = (
                    primary_text if isinstance(primary_text, list) else [primary_text]
                )
                failed_indices = list(detailed.failed_indices)
                primary_ok = detailed.result.success
                primary_error = detailed.result.error_message
                learned_dict = detailed.term_dict
            else:  # 兼容仅实现 translate() 的后端（测试 fake 等）
                legacy = self.llm_backend.translate(request)
                legacy_text = legacy.translated_text
                translations = (
                    legacy_text if isinstance(legacy_text, list) else [legacy_text]
                )
                failed_indices = []
                primary_ok = legacy.success
                primary_error = legacy.error_message
                learned_dict = None
            if not primary_ok:
                raise ProcessingError(
                    message="LLM translation failed",
                    context={"details": primary_error},
                )

            remote_ok = len(texts) - len(failed_indices)
            fallback_ok = 0

            if failed_indices and self._fallback_backend is not None:
                failed_texts = [texts[i] for i in failed_indices]
                log_info(
                    "[TranslationEngine] Falling back to local model for "
                    f"{len(failed_texts)} sentence(s)"
                )
                fallback_request = TranslationRequest(
                    text=failed_texts,
                    src_lang=src_lang,
                    tgt_lang=tgt_lang,
                    cancelled_callback=cancelled_callback,
                )
                fallback_result = self._fallback_backend.translate_detailed(
                    fallback_request, term_dict=learned_dict
                )
                used_local_model = self._fallback_model_name
                if fallback_result.result.success:
                    fallback_translations = fallback_result.result.translated_text
                    if isinstance(fallback_translations, str):
                        fallback_translations = [fallback_translations]
                    fallback_failed = set(fallback_result.failed_indices)
                    for j, idx in enumerate(failed_indices):
                        if j not in fallback_failed:
                            translations[idx] = fallback_translations[j]
                            fallback_ok += 1

            stats = {
                "total": len(texts),
                "remote": remote_ok,
                "fallback": fallback_ok,
                "failed": len(texts) - remote_ok - fallback_ok,
            }
            return TranslationOutcome(translations=translations, stats=stats)
        finally:
            self._unload_local_model(used_local_model)

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
            user_terms=self.user_terms,
        )

        log_debug(
            f"[LLM Translation] Sending request: {len(texts)} segments, "
            f"src={src_lang}, tgt={tgt_lang}"
        )

        log_step("Calling LLM API...")
        outcome = self.translate_texts(texts, src_lang, tgt_lang, progress)

        # 合并结果到 segments
        translated_segments = self._merge_translation_result(
            segments, outcome.translations
        )

        log_info(f"Translation completed: {len(translated_segments)} segments")

        translated_result = result.copy()
        translated_result["segments"] = translated_segments
        translated_result["translation_stats"] = outcome.stats
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
