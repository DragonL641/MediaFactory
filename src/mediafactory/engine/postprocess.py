"""转录后处理引擎（智能断句 + 说话人分离）

使用 stable-ts 进行智能断句（regroup），使用 pyannote.audio 进行说话人分离。
两个功能均为容错设计：处理失败时返回原始 segments 并记录警告。
"""

from typing import Any, Dict, List, Optional

from ..logging import log_info, log_warning, log_debug
from ..core.exception_wrapper import convert_exception


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
            处理后的 segments 列表，失败时返回原始 segments
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
            whisper_result.merge_by_gap(
                max_gap=merge_gap_threshold,
                max_words=float("inf"),
            )

            # 转回 MediaFactory 格式
            result_segments = self._whisper_result_to_segments(whisper_result)

            log_info(
                f"Resegmentation complete: {len(segments)} -> {len(result_segments)} segments"
            )
            return result_segments

        except Exception as e:
            wrapped = convert_exception(
                e, context={"operation": "resegmentation", "segment_count": len(segments)}
            )
            log_warning(
                f"Resegmentation failed, returning original segments: {wrapped.message}"
            )
            return segments

    def diarize(
        self,
        segments: List[Dict[str, Any]],
        audio_path: str,
        num_speakers: int = 0,
    ) -> List[Dict[str, Any]]:
        """说话人分离：使用 pyannote.audio 标注说话人

        Args:
            segments: MediaFactory 格式的 segments 列表
            audio_path: 音频文件路径
            num_speakers: 说话人数量（0=自动检测）

        Returns:
            添加了 speaker 字段的 segments 列表，失败时返回原始 segments
        """
        if not segments:
            log_debug("No segments to diarize, returning empty list")
            return segments

        try:
            from pyannote.audio import Pipeline as PyannotePipeline

            # 尝试加载 pyannote 说话人分离模型
            # 需要用户在 HuggingFace 接受 pyannote/speaker-diarization-3.1 协议
            import torch

            log_info("Loading pyannote speaker diarization model...")
            diarization_pipeline = PyannotePipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=True,
            )

            # 选择设备
            device = "cuda" if torch.cuda.is_available() else "cpu"
            diarization_pipeline.to(torch.device(device))

            log_info(f"Running speaker diarization on {device}...")

            # 执行说话人分离
            diarization_kwargs = {}
            if num_speakers > 0:
                diarization_kwargs["num_speakers"] = num_speakers

            diarization_result = diarization_pipeline(audio_path, **diarization_kwargs)

            # 将说话人标签映射到 segments
            result_segments = self._assign_speakers(segments, diarization_result)

            # 统计说话人数量
            speakers = set(
                seg.get("speaker", "") for seg in result_segments if seg.get("speaker")
            )
            log_info(
                f"Diarization complete: {len(speakers)} speakers detected "
                f"across {len(result_segments)} segments"
            )
            return result_segments

        except ImportError:
            log_warning(
                "pyannote.audio not installed, skipping diarization. "
                "Install with: pip install pyannote.audio"
            )
            return segments

        except Exception as e:
            wrapped = convert_exception(
                e, context={"operation": "diarization", "audio_path": audio_path}
            )
            log_warning(
                f"Diarization failed, returning original segments: {wrapped.message}"
            )
            return segments

    def _whisper_result_to_segments(
        self, whisper_result: Any
    ) -> List[Dict[str, Any]]:
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

    def _assign_speakers(
        self,
        segments: List[Dict[str, Any]],
        diarization_result: Any,
    ) -> List[Dict[str, Any]]:
        """将说话人标签分配到 segments

        策略：对每个 segment，找到与其时间范围重叠最多的说话人。

        Args:
            segments: MediaFactory segments
            diarization_result: pyannote 说话人分离结果

        Returns:
            添加了 speaker 字段的 segments
        """
        result = []
        for seg in segments:
            seg_start = seg["start"]
            seg_end = seg["end"]
            seg_duration = seg_end - seg_start

            # 计算每个说话人在此 segment 时间范围内的重叠时长
            speaker_overlap: Dict[str, float] = {}

            for turn, _, speaker in diarization_result.itertracks(yield_label=True):
                # 计算重叠
                overlap_start = max(seg_start, turn.start)
                overlap_end = min(seg_end, turn.end)
                overlap = overlap_end - overlap_start

                if overlap > 0:
                    speaker_overlap[speaker] = (
                        speaker_overlap.get(speaker, 0.0) + overlap
                    )

            # 选择重叠最多的说话人
            if speaker_overlap:
                best_speaker = max(speaker_overlap, key=speaker_overlap.get)
                # 只有重叠占比超过 50% 才分配说话人标签
                if seg_duration > 0 and speaker_overlap[best_speaker] / seg_duration > 0.5:
                    seg_copy = {**seg, "speaker": best_speaker}
                else:
                    seg_copy = {**seg, "speaker": ""}
            else:
                seg_copy = {**seg, "speaker": ""}

            result.append(seg_copy)

        return result
