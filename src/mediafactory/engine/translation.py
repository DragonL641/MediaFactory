"""翻译引擎模块

统一接口，内部实现本地翻译和 LLM 翻译。
"""

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
                        "Source language not specified or detected. Skipping translation."
                    )
                    return result

                if actual_src_lang == tgt_lang:
                    log_debug(
                        "Source and target languages are the same, skipping translation"
                    )
                    return result

                # 选择翻译方式
                if self._use_llm:
                    return self._translate_with_llm(
                        result, actual_src_lang, tgt_lang, progress
                    )
                else:
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
        log_info(f"[TranslationEngine] This may take a while for large models (e.g., MADLAD400-3B)")
        log_debug(f"[TranslationEngine] Calling progress.update(5, 'Loading translation model...')")
        progress.update(5, "Loading translation model...")

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
        progress.update(15, "Translation model loaded, starting translation...")

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
        """本地模型分段翻译"""
        from ..models.local_models import local_model_manager

        if not segments:
            return segments

        translated_segments = []
        total_segments = len(segments)

        src_code = local_model_manager.get_lang_code(src_lang, self.model_type)
        tgt_code = local_model_manager.get_lang_code(tgt_lang, self.model_type)

        log_debug(f"[LocalTranslation] src_lang={src_lang} -> src_code={src_code}")
        log_debug(f"[LocalTranslation] tgt_lang={tgt_lang} -> tgt_code={tgt_code}")

        for i, segment in enumerate(segments):
            if progress.is_cancelled():
                raise OperationCancelledError(
                    message="Translation cancelled by user",
                    context={"model_type": self.model_type, "segment_index": i},
                )

            current_segment_num = i + TranslationConstants.SEGMENT_NUMBER_OFFSET
            progress_value = (current_segment_num / total_segments) * 100
            progress.update(
                progress_value, f"分段: {current_segment_num}/{total_segments}"
            )

            original_text = segment["text"].strip()
            if not original_text:
                translated_segments.append(segment.copy())
                continue

            translated_text = self._perform_multilingual_translation(
                original_text, src_code, tgt_code, model_callable
            )

            new_segment = segment.copy()
            new_segment["original_text"] = original_text
            new_segment["text"] = translated_text
            translated_segments.append(new_segment)

        progress.update(100.0, "已完成")
        return translated_segments

    def _perform_multilingual_translation(
        self, text: str, src_code: str, tgt_code: str, model_callable: Any
    ) -> str:
        """执行多语言翻译"""
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
        """使用 LLM API 翻译"""
        from ..llm import TranslationRequest

        backend_type = type(self.llm_backend).__name__
        model_name = self.llm_backend.get_model_name

        # 测试 API 连接
        self._test_api_connection()

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

        # 处理结果
        translated_segments = []

        if isinstance(translation_result.translated_text, str):
            for i, seg in enumerate(segments):
                new_seg = seg.copy()
                new_seg["original_text"] = seg.get("text", "")
                if i == 0:
                    new_seg["text"] = translation_result.translated_text
                else:
                    new_seg["text"] = seg.get("text", "")
                translated_segments.append(new_seg)
        elif isinstance(translation_result.translated_text, list):
            translated_texts = translation_result.translated_text
            for i, seg in enumerate(segments):
                new_seg = seg.copy()
                new_seg["original_text"] = seg.get("text", "")
                if i < len(translated_texts):
                    new_seg["text"] = translated_texts[i]
                else:
                    new_seg["text"] = seg.get("text", "")
                translated_segments.append(new_seg)
        else:
            translated_segments = [seg.copy() for seg in segments]

        log_info(f"Translation completed: {len(translated_segments)} segments")

        translated_result = result.copy()
        translated_result["segments"] = translated_segments
        return translated_result

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
