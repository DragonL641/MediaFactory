"""语音识别引擎（Faster Whisper）"""

from typing import Dict, Any, Optional
from ..logging import log_step, log_info, log_warning, log_error
from ..config import get_config_manager
from ..utils.time_estimator import TimeEstimator
from ..core.progress_protocol import ProgressCallback, NO_OP_PROGRESS
from ..exceptions import ProcessingError, OperationCancelledError
from ..core.exception_wrapper import wrap_exceptions, convert_exception
from ..i18n import t
import time
import tqdm


# =============================================================================
# 识别引擎常量（从 constants.py 移入）
# =============================================================================


class RecognitionConstants:
    """识别引擎相关常量。"""

    PROGRESS_UPDATE_INTERVAL = 0.1  # 进度更新间隔（秒）
    LOG_INTERVAL_SECONDS = 5.0  # 详细日志间隔
    SEGMENT_LOG_THRESHOLD = 10  # 每 N 个分段记录一次日志


class ProgressConstants:
    """进度更新相关常量。"""

    MAX_PROGRESS = 100  # 最大进度值
    NEAR_COMPLETE = 99  # 接近完成的进度值


def _get_decode_audio():
    """获取 decode_audio 函数（懒加载）"""
    try:
        from faster_whisper import decode_audio

        return decode_audio
    except ImportError as e:
        raise ProcessingError(
            message=t("error.fasterWhisperNotInstalled"),
            context={"missing_dependency": "faster-whisper"},
        ) from e


class RecognitionEngine:
    """语音识别引擎（Faster Whisper）"""

    def detect_language_only(
        self,
        model: Any,
        audio_path: str,
        progress: Optional[ProgressCallback] = None,
    ) -> Dict[str, Any]:
        """仅检测音频语言"""
        if progress is None:
            progress = NO_OP_PROGRESS

        progress.update(0, t("progress.detectingLanguage"))
        log_step("Running dedicated language detection...")

        decode_audio = _get_decode_audio()

        try:
            with wrap_exceptions(
                context={"audio_path": audio_path},
                operation="whisper_language_detection",
            ):
                audio_array = decode_audio(audio_path)
                detected_lang, probability, language_info = model.detect_language(
                    audio=audio_array
                )

                progress.update(100, t("progress.languageDetectionCompleted"))
                log_info(
                    f"Language detected: {detected_lang} (confidence: {probability:.2%})"
                )

                return {
                    "language": detected_lang,
                    "language_probability": probability,
                }

        except OperationCancelledError:
            raise
        except Exception as e:
            raise ProcessingError(
                message=f"Language detection failed: {e}",
                context={"audio_path": audio_path, "error": str(e)},
            ) from e

    def transcribe(
        self,
        model: Any,
        audio_path: str,
        src_lang: Optional[str] = None,
        progress: Optional[ProgressCallback] = None,
    ) -> Dict[str, Any]:
        """执行音频转录"""
        if progress is None:
            progress = NO_OP_PROGRESS
        return self._transcribe_with_whisper(model, audio_path, src_lang, progress)

    def _transcribe_with_whisper(
        self,
        model: Any,
        audio_path: str,
        src_lang: Optional[str] = None,
        progress: ProgressCallback = NO_OP_PROGRESS,
    ) -> Dict[str, Any]:
        """Faster Whisper 转录"""
        log_step("Starting high-quality transcription...")

        model_name = getattr(model, "model_size", "large-v3")

        # 支持取消的 tqdm
        class CancelableTqdm(tqdm.tqdm):
            def update(self, n=1):
                if progress.is_cancelled():
                    raise OperationCancelledError(
                        message=t("error.transcriptionCancelled"),
                        context={"audio_path": audio_path, "model": model_name},
                    )
                return super().update(n)

        whisper_lang = None if (not src_lang or src_lang == "auto") else src_lang
        if whisper_lang:
            log_info(f"Using detected language: {whisper_lang}")
        else:
            log_info("Language set to auto-detection")

        # 从配置加载参数
        config_manager = get_config_manager()
        config = config_manager.config
        transcribe_kwargs = {
            "language": whisper_lang,
            "task": "transcribe",
            "beam_size": config.whisper.beam_size,
            "patience": config.whisper.patience,
            "length_penalty": config.whisper.length_penalty,
            "no_speech_threshold": config.whisper.no_speech_threshold,
            "condition_on_previous_text": config.whisper.condition_on_previous_text,
            "initial_prompt": None,
            "word_timestamps": config.whisper.word_timestamps,
        }

        # VAD 配置
        if config.whisper.vad_filter:
            transcribe_kwargs["vad_filter"] = True
            transcribe_kwargs["vad_parameters"] = {
                "threshold": config.whisper.vad_threshold,
                "min_speech_duration_ms": config.whisper.vad_min_speech_duration_ms,
                "min_silence_duration_ms": config.whisper.vad_min_silence_duration_ms,
                "speech_pad_ms": config.whisper.vad_speech_pad_ms,
            }
            log_info(f"VAD enabled: threshold={config.whisper.vad_threshold}")

        # 进度跟踪
        duration = TimeEstimator.get_video_duration(audio_path) or 0
        estimated_time = TimeEstimator.estimate_whisper_transcription_time(
            duration,
            beam_size=config.whisper.beam_size,
            has_word_timestamps=config.whisper.word_timestamps,
        )

        original_tqdm = tqdm.tqdm
        tqdm.tqdm = CancelableTqdm
        try:
            with wrap_exceptions(
                context={
                    "audio_path": audio_path,
                    "model": model_name,
                    "duration": duration,
                    "src_lang": whisper_lang,
                },
                operation="whisper_transcription",
            ):
                segments_generator, info = model.transcribe(
                    audio_path, **transcribe_kwargs
                )

                total_duration = (
                    info.duration if hasattr(info, "duration") else duration
                )

                segments_list = []
                processed_duration = 0.0
                segment_count = 0
                last_log_time = time.time()
                last_progress_update_time = time.time()
                processing_start_time = time.time()

                # 在循环开始前立即报告初始进度
                if total_duration > 0:
                    progress.update(5, t("progress.analyzingAudio"))

                for segment in segments_generator:
                    if progress.is_cancelled():
                        raise OperationCancelledError(
                            message=t("error.transcriptionCancelled"),
                            context={"audio_path": audio_path, "model": model_name},
                        )

                    segment_end = segment.end if hasattr(segment, "end") else 0
                    processed_duration = max(processed_duration, segment_end)

                    if total_duration > 0:
                        current_time = time.time()

                        # 计算进度值
                        if processed_duration > 0:
                            # 基于已处理的音频时长计算进度
                            progress_value = min(
                                (processed_duration / total_duration) * 100,
                                ProgressConstants.NEAR_COMPLETE,
                            )
                        else:
                            # 还没有分段时，基于处理时间估算进度
                            # 假设处理速度约为实时速度的0.3倍（Whisper典型速度）
                            elapsed = current_time - processing_start_time
                            estimated_audio_processed = elapsed * 0.3
                            progress_value = min(
                                5 + (estimated_audio_processed / total_duration) * 90,
                                ProgressConstants.NEAR_COMPLETE - 10,
                            )

                        if (
                            current_time - last_progress_update_time
                            >= RecognitionConstants.PROGRESS_UPDATE_INTERVAL
                        ):
                            if processed_duration > 0:
                                progress.update(
                                    progress_value,
                                    t("progress.processingAudio", processed=f"{processed_duration:.1f}s", total=f"{total_duration:.1f}s"),
                                )
                            else:
                                progress.update(progress_value, t("progress.analyzingAudio"))
                            last_progress_update_time = current_time

                        segment_count += 1
                        if (
                            current_time - last_log_time
                            >= RecognitionConstants.LOG_INTERVAL_SECONDS
                            or segment_count
                            % RecognitionConstants.SEGMENT_LOG_THRESHOLD
                            == 0
                        ):
                            log_info(
                                f"进度: {progress_value:.0f}%, 已处理 {processed_duration:.1f}s/{total_duration:.1f}s, 分段数: {segment_count}"
                            )
                            last_log_time = current_time

                    segments_list.append(segment)

                progress.update(ProgressConstants.MAX_PROGRESS, t("progress.completed"))

                result = {
                    "segments": [],
                    "text": "",
                    "language": (
                        info.language if hasattr(info, "language") else "unknown"
                    ),
                    "language_probability": getattr(info, "language_probability", 0.0),
                }

                for segment in segments_list:
                    segment_dict = {
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text.strip(),
                        "id": segment.id if hasattr(segment, "id") else None,
                    }

                    if segment.words:
                        segment_dict["words"] = [
                            {
                                "start": word.start,
                                "end": word.end,
                                "word": word.word,
                                "probability": word.probability,
                            }
                            for word in segment.words
                        ]

                    result["segments"].append(segment_dict)

                result["text"] = " ".join(
                    seg["text"].strip() for seg in result["segments"]
                )

        except ProcessingError:
            raise
        except OperationCancelledError:
            log_warning("Recognition cancelled by user")
            raise
        except Exception as e:
            error_msg = str(e).lower()
            log_error(f"Transcription failed: {e}")

            if (
                "out of memory" in error_msg
                or "memory" in error_msg
                or "cuda" in error_msg
            ):
                raise ProcessingError(
                    message="Transcription failed due to memory error",
                    context={
                        "audio_path": audio_path,
                        "model": model_name,
                        "error": str(e),
                    },
                ) from e
            elif "file" in error_msg or "audio" in error_msg:
                raise ProcessingError(
                    message="Transcription failed due to audio file error",
                    context={"audio_path": audio_path, "error": str(e)},
                ) from e
            else:
                raise convert_exception(
                    e, context={"audio_path": audio_path, "model": model_name}
                ) from e
        finally:
            tqdm.tqdm = original_tqdm

        log_info(
            f"Transcription completed, {len(result['segments'])} segments in total"
        )

        if not result.get("segments"):
            log_warning("No speech segments detected. Possible reasons:")
            log_warning("  1. Audio file has no speech content or volume too low")
            log_warning("  2. Audio language doesn't match set language")
            log_warning("  3. Audio quality too low")

        # 使用词级时间戳校正分段边界
        word_timestamps_enabled = transcribe_kwargs.get("word_timestamps", False)
        segments = result.get("segments", [])

        if word_timestamps_enabled and segments:
            corrected_count = 0
            no_words_count = 0

            for segment in segments:
                words = segment.get("words", [])
                if words:
                    old_start = segment["start"]
                    old_end = segment["end"]
                    new_start = words[0].get("start", old_start)
                    new_end = words[-1].get("end", old_end)
                    segment["start"] = new_start
                    segment["end"] = new_end
                    if (
                        abs(old_start - new_start) > 0.001
                        or abs(old_end - new_end) > 0.001
                    ):
                        corrected_count += 1
                else:
                    no_words_count += 1

            log_info(
                f"Word-level timestamp correction: {corrected_count} segments adjusted, "
                f"{no_words_count} segments without word data"
            )
            if no_words_count > 0:
                log_warning(
                    f"{no_words_count} segments missing word-level timestamps, "
                    "using original segment boundaries"
                )
        elif word_timestamps_enabled:
            log_warning(
                "word_timestamps enabled but no segments available for correction"
            )
        else:
            log_info("word_timestamps disabled, using original segment boundaries")

        return result
