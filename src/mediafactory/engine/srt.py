"""SRT/VTT 字幕引擎，支持双语字幕"""

import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..exceptions import ProcessingError
from ..core.exception_wrapper import convert_exception


# =============================================================================
# 字幕格式常量（从 constants.py 移入）
# =============================================================================


class SubtitleFormatConstants:
    """字幕文件格式常量。"""

    # 时间转换
    SECONDS_PER_HOUR = 3600
    SECONDS_PER_MINUTE = 60
    MILLISECONDS_PER_SECOND = 1000

    # VTT 格式
    VTT_HEADER_TEXT = "WEBVTT"
    VTT_HEADER_LENGTH = len("WEBVTT\n\n")  # VTT 头部长度

    # 最小行数验证
    MIN_SRT_BLOCK_LINES = 3  # 有效 SRT 块最小行数
    MIN_VTT_BLOCK_LINES = 2  # 有效 VTT 块最小行数


class BilingualLayout:
    """双语字幕布局选项。"""

    TRANSLATE_ON_TOP = "translate_on_top"  # 译文在上
    ORIGINAL_ON_TOP = "original_on_top"  # 原文在上
    ONLY_TRANSLATE = "translate_only"  # 仅显示译文
    ONLY_ORIGINAL = "original_only"  # 仅显示原文


class SRTEngine:
    """SRT/VTT 字幕解析和生成"""

    TIMESTAMP_PATTERN = re.compile(
        r"(\d{2}):(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[.,](\d{3})"
    )

    def parse(self, filepath: str) -> List[Dict[str, Any]]:
        """解析字幕文件（SRT/VTT）"""
        ext = Path(filepath).suffix.lower()

        if ext == ".srt":
            return self._parse_srt(filepath)
        elif ext == ".vtt":
            return self._parse_vtt(filepath)
        else:
            raise ProcessingError(
                message=f"Unsupported subtitle format: {ext}",
                context={"filepath": filepath, "extension": ext},
            )

    def _parse_srt(self, filepath: str) -> List[Dict[str, Any]]:
        """解析 SRT 文件"""
        segments = []

        try:
            if not os.path.exists(filepath):
                raise ProcessingError(
                    message=f"Subtitle file not found: {filepath}",
                    context={"filepath": filepath},
                )

            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except ProcessingError:
            raise
        except Exception as e:
            raise convert_exception(e, context={"filepath": filepath}) from e

        blocks = re.split(r"\n\s*\n", content.strip())

        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) < SubtitleFormatConstants.MIN_SRT_BLOCK_LINES:
                continue

            timestamp_line = lines[1]
            match = self.TIMESTAMP_PATTERN.search(timestamp_line)

            if match:
                start = self._parse_timestamp(
                    match.group(1), match.group(2), match.group(3), match.group(4)
                )
                end = self._parse_timestamp(
                    match.group(5), match.group(6), match.group(7), match.group(8)
                )
                text = "\n".join(lines[2:]).strip()

                segments.append({"start": start, "end": end, "text": text})

        return segments

    def _parse_vtt(self, filepath: str) -> List[Dict[str, Any]]:
        """解析 VTT 文件"""
        segments = []

        try:
            if not os.path.exists(filepath):
                raise ProcessingError(
                    message=f"Subtitle file not found: {filepath}",
                    context={"filepath": filepath},
                )

            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except ProcessingError:
            raise
        except Exception as e:
            raise convert_exception(e, context={"filepath": filepath}) from e

        if content.startswith(SubtitleFormatConstants.VTT_HEADER_TEXT):
            content = content[SubtitleFormatConstants.VTT_HEADER_LENGTH :]

        blocks = re.split(r"\n\s*\n", content.strip())

        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) < SubtitleFormatConstants.MIN_VTT_BLOCK_LINES:
                continue

            timestamp_line = None
            text_start_idx = 0

            for i, line in enumerate(lines):
                if "-->" in line:
                    timestamp_line = line
                    text_start_idx = i + 1
                    break

            if not timestamp_line:
                continue

            match = self.TIMESTAMP_PATTERN.search(timestamp_line)

            if match:
                start = self._parse_timestamp(
                    match.group(1), match.group(2), match.group(3), match.group(4)
                )
                end = self._parse_timestamp(
                    match.group(5), match.group(6), match.group(7), match.group(8)
                )
                text = "\n".join(lines[text_start_idx:]).strip()

                if text:
                    segments.append({"start": start, "end": end, "text": text})

        return segments

    def _parse_timestamp(
        self, hours: str, minutes: str, seconds: str, millis: str
    ) -> float:
        """解析时间戳为秒数"""
        return (
            int(hours) * SubtitleFormatConstants.SECONDS_PER_HOUR
            + int(minutes) * SubtitleFormatConstants.SECONDS_PER_MINUTE
            + int(seconds)
            + int(millis) / SubtitleFormatConstants.MILLISECONDS_PER_SECOND
        )

    def generate(self, result: Dict[str, Any], output_path: str) -> None:
        """生成字幕文件（兼容旧接口）"""
        self.generate_to_path(output_path, result.get("segments", []))

    def generate_to_path(
        self,
        output_path: str,
        segments: List[Dict[str, Any]],
        bilingual: bool = False,
        layout: str = BilingualLayout.TRANSLATE_ON_TOP,
    ) -> None:
        """生成字幕到指定路径

        Args:
            output_path: 输出文件路径
            segments: 字幕分段列表（start, end, text, original_text）
            bilingual: 是否双语字幕
            layout: 双语布局（translate_on_top/original_on_top/only_translate/only_original）
        """
        ext = Path(output_path).suffix.lower()

        try:
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                if ext == ".vtt":
                    f.write("WEBVTT\n\n")

                for i, segment in enumerate(segments, 1):
                    start = segment.get("start", 0)
                    end = segment.get("end", 0)
                    text = segment.get("text", "").strip()
                    original_text = segment.get("original_text", "").strip()

                    # 说话人标签处理（语音分离后 segment 包含 speaker 字段）
                    speaker = segment.get("speaker", "")
                    if speaker:
                        text = f"[{speaker}] {text}"
                        if original_text:
                            original_text = f"[{speaker}] {original_text}"

                    # 双语处理
                    if bilingual and original_text:
                        if layout == BilingualLayout.TRANSLATE_ON_TOP:
                            text = f"{text}\n{original_text}"
                        elif layout == BilingualLayout.ORIGINAL_ON_TOP:
                            text = f"{original_text}\n{text}"
                        elif layout == BilingualLayout.ONLY_ORIGINAL:
                            text = original_text

                    f.write(f"{i}\n")
                    if ext == ".vtt":
                        f.write(
                            f"{self._format_timestamp_vtt(start)} --> {self._format_timestamp_vtt(end)}\n"
                        )
                    else:
                        f.write(
                            f"{self._format_timestamp(start)} --> {self._format_timestamp(end)}\n"
                        )
                    f.write(f"{text}\n\n")
        except Exception as e:
            raise convert_exception(
                e, context={"output_path": output_path, "segment_count": len(segments)}
            ) from e

    def _format_timestamp(self, seconds: float) -> str:
        """格式化为 SRT 时间戳（HH:MM:SS,mmm）"""
        hours = int(seconds // SubtitleFormatConstants.SECONDS_PER_HOUR)
        minutes = int(
            (seconds % SubtitleFormatConstants.SECONDS_PER_HOUR)
            // SubtitleFormatConstants.SECONDS_PER_MINUTE
        )
        secs = int(seconds % SubtitleFormatConstants.SECONDS_PER_MINUTE)
        millis = int(
            (seconds - int(seconds)) * SubtitleFormatConstants.MILLISECONDS_PER_SECOND
        )
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _format_timestamp_vtt(self, seconds: float) -> str:
        """格式化为 VTT 时间戳（HH:MM:SS.mmm）"""
        hours = int(seconds // SubtitleFormatConstants.SECONDS_PER_HOUR)
        minutes = int(
            (seconds % SubtitleFormatConstants.SECONDS_PER_HOUR)
            // SubtitleFormatConstants.SECONDS_PER_MINUTE
        )
        secs = int(seconds % SubtitleFormatConstants.SECONDS_PER_MINUTE)
        millis = int(
            (seconds - int(seconds)) * SubtitleFormatConstants.MILLISECONDS_PER_SECOND
        )
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    def detect_bilingual(
        self, segments: List[Dict[str, Any]], threshold: float = 0.8
    ) -> bool:
        """检测字幕是否为双语字幕

        双语字幕的典型特征：一个时间戳下有两行文字（一行原文，一行译文）

        Args:
            segments: 解析后的字幕分段列表
            threshold: 判定阈值（默认80%，避免误报单语字幕中的少量多行注释）

        Returns:
            True 表示双语字幕，False 表示单语字幕
        """
        if not segments:
            return False

        multiline_count = sum(1 for seg in segments if "\n" in seg.get("text", ""))
        return (multiline_count / len(segments)) >= threshold

    def generate_text_to_path(
        self,
        output_path: str,
        segments: List[Dict[str, Any]],
    ) -> None:
        """生成纯文本文件（每句一行，无时间戳）

        Args:
            output_path: 输出文件路径
            segments: 字幕分段列表（start, end, text）
        """
        try:
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                for segment in segments:
                    text = segment.get("text", "").strip()
                    if text:
                        f.write(text + "\n")
        except Exception as e:
            raise convert_exception(
                e, context={"output_path": output_path, "segment_count": len(segments)}
            ) from e
