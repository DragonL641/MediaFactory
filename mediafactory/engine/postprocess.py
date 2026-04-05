"""转录后处理引擎（智能断句）

使用 stable-ts 进行智能断句（regroup）。
当执行失败时，抛出异常以通知上层终止任务。
"""

from typing import Any, Dict, List, Optional

from ..logging import log_info, log_warning, log_debug, log_error
from ..core.exception_wrapper import convert_exception
from ..exceptions import ProcessingError


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
    ) -> List[Dict[str, Any]]:
        """智能断句：使用 stable-ts regroup 重新组织分段

        Args:
            segments: MediaFactory 格式的 segments 列表
            max_chars_cjk: CJK 单条字幕最大字符数
            max_chars_latin: Latin 单条字幕最大字符数
            min_duration: 最短持续时间（秒）
            max_duration: 最长持续时间（秒）
            merge_gap_threshold: 合并间隔阈值（秒）

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

            # MediaFactory segments -> WhisperResult
            whisper_result = stable_whisper.WhisperResult(segments)

            # 构建 regroup 算法字符串
            # 语法: sg=分割间隔, sp=标点分割, sl=长度分割, cm=最大时长, mg=合并间隔
            regroup_algo = (
                f"sg={merge_gap_threshold}"
                f"_sl={max_chars_latin}"
                f"_cm={max_duration}"
            )

            log_info(f"Running resegmentation with algo: {regroup_algo}")
            whisper_result.regroup(regroup_algo=regroup_algo)

            # 应用最短时长：过短的分段与相邻分段合并
            # stable-ts >= 2.17.0: merge_by_gap 第一个参数为位置参数 gap
            whisper_result.merge_by_gap(
                merge_gap_threshold,
                max_words=float("inf"),
            )

            # 转回 MediaFactory 格式
            result_segments = self._whisper_result_to_segments(whisper_result)

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
