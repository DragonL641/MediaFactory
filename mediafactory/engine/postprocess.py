"""转录后处理引擎（智能断句）

使用 stable-ts 进行智能断句（regroup）。
当执行失败时，抛出异常以通知上层终止任务。
"""

from typing import Any, Dict, List, Optional

from ..logging import log_info, log_warning, log_debug, log_error
from ..core.exception_wrapper import convert_exception
from ..exceptions import ProcessingError
from ..constants import CJK_LANG_CODES


class PostProcessEngine:
    """转录后处理引擎"""

    def resegment(
        self,
        segments: List[Dict[str, Any]],
        max_chars_cjk: int = 42,
        max_chars_latin: int = 80,
        min_duration: float = 1.0,
        max_duration: float = 7.0,
        merge_gap_threshold: float = 0.3,
        language: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """智能断句：使用 stable-ts regroup 重新组织分段

        Args:
            segments: MediaFactory 格式的 segments 列表
            max_chars_cjk: CJK 单条字幕最大字符数
            max_chars_latin: Latin 单条字幕最大字符数
            min_duration: 最短持续时间（秒），低于此值的分段与相邻分段合并
            max_duration: 最长持续时间（秒）
            merge_gap_threshold: 合并间隔阈值（秒）
            language: 检测到的语言代码（用于选择 CJK/Latin 参数）

        Returns:
            处理后的 segments 列表

        Raises:
            ProcessingError: 智能断句执行失败
        """
        if not segments:
            log_debug("No segments to resegment, returning empty list")
            return segments

        # 检查是否有 word-level timestamps
        has_words = any(seg.get("words") for seg in segments)
        if not has_words:
            log_warning(
                "Segments lack word-level timestamps, skipping resegmentation. "
                "Enable word_timestamps in Whisper config for best results."
            )
            return segments

        try:
            import stable_whisper

            # 根据语言选择合适的字符数上限
            is_cjk = language in CJK_LANG_CODES if language else False
            max_chars = max_chars_cjk if is_cjk else max_chars_latin

            # MediaFactory segments -> WhisperResult
            whisper_result = stable_whisper.WhisperResult(segments)

            # 构建 regroup 算法字符串
            # 语法: sg=分割间隔, sl=长度分割, cm=最大时长
            regroup_algo = (
                f"sg={merge_gap_threshold}"
                f"_sl={max_chars}"
                f"_cm={max_duration}"
            )

            log_info(f"Running resegmentation with algo: {regroup_algo} (lang={language}, cjk={is_cjk})")
            whisper_result.regroup(regroup_algo=regroup_algo)

            # 合并相邻短间隔分段
            whisper_result.merge_by_gap(
                merge_gap_threshold,
                max_words=float("inf"),
            )

            # 转回 MediaFactory 格式
            result_segments = self._whisper_result_to_segments(whisper_result)

            # 合并过短的分段（min_duration 生效）
            if min_duration > 0:
                result_segments = self._merge_short_segments(
                    result_segments, min_duration, merge_gap_threshold
                )

            log_info(
                f"Resegmentation complete: {len(segments)} -> {len(result_segments)} segments"
            )
            return result_segments

        except ImportError as e:
            log_warning(f"stable-ts not installed, skipping resegmentation: {e}")
            return segments

        except Exception as e:
            log_error(f"Resegmentation failed: {e}")
            raise ProcessingError(
                message=f"Resegmentation failed: {e}",
                context={"operation": "resegmentation", "segment_count": len(segments)},
            ) from e

    def _merge_short_segments(
        self,
        segments: List[Dict[str, Any]],
        min_duration: float,
        max_gap: float,
    ) -> List[Dict[str, Any]]:
        """将过短的分段与相邻分段合并

        优先向后合并（与下一段拼接），间隔超过 max_gap 的不合并。
        """
        if len(segments) <= 1:
            return segments

        merged = [segments[0]]
        for seg in segments[1:]:
            prev = merged[-1]
            duration = seg["end"] - seg["start"]

            # 当前分段过短，且与前一分段间隔足够小
            if duration < min_duration:
                gap = seg["start"] - prev["end"]
                if gap <= max_gap:
                    # 合并：扩展前一分段的结束时间和文本
                    prev["end"] = max(prev["end"], seg["end"])
                    prev["text"] = (prev["text"] + seg["text"]).strip()
                    # 合并 words
                    if prev.get("words") and seg.get("words"):
                        prev["words"].extend(seg["words"])
                    continue

            merged.append(seg)

        if len(merged) < len(segments):
            log_info(
                f"Merged short segments: {len(segments)} -> {len(merged)} "
                f"(min_duration={min_duration}s)"
            )

        return merged

    def _whisper_result_to_segments(self, whisper_result: Any) -> List[Dict[str, Any]]:
        """将 stable-ts WhisperResult 转换为 MediaFactory segments 格式

        Args:
            whisper_result: stable_whisper.WhisperResult 实例

        Returns:
            MediaFactory 格式的 segments 列表
        """
        result = []
        for i, seg in enumerate(whisper_result.segments):
            segment_dict: Dict[str, Any] = {
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip(),
                "id": i,
            }

            # 保留 word-level timestamps
            if hasattr(seg, "words") and seg.words:
                segment_dict["words"] = [
                    {
                        "start": word.start,
                        "end": word.end,
                        "word": word.word,
                        "probability": word.probability,
                    }
                    for word in seg.words
                ]

            result.append(segment_dict)

        return result
