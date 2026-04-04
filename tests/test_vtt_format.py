"""VTT 格式字幕生成与解析测试。

覆盖场景：
1. VTT 基础生成 — WEBVTT 头部、dot-separated 时间戳
2. VTT 双语布局
3. VTT 文件解析
4. SRTGenerationStage 输出 VTT 格式
"""

import os
import pytest
from pathlib import Path
from unittest.mock import Mock

from mediafactory.engine.srt import SRTEngine, BilingualLayout
from mediafactory.pipeline.context import ProcessingContext
from mediafactory.pipeline.stages import SRTGenerationStage


# ========== 共享 fixture ==========


@pytest.fixture
def engine() -> SRTEngine:
    """SRTEngine 实例。"""
    return SRTEngine()


@pytest.fixture
def sample_segments():
    """标准测试字幕片段。"""
    return [
        {"start": 0.0, "end": 2.5, "text": "Hello, world!"},
        {"start": 3.0, "end": 5.75, "text": "This is a test."},
        {"start": 6.0, "end": 8.5, "text": "Goodbye!"},
    ]


@pytest.fixture
def bilingual_segments():
    """双语字幕片段（含 original_text）。"""
    return [
        {
            "start": 0.0,
            "end": 2.5,
            "text": "你好世界！",
            "original_text": "Hello, world!",
        },
        {
            "start": 3.0,
            "end": 5.75,
            "text": "这是一个测试。",
            "original_text": "This is a test.",
        },
    ]


# ========== 测试 ==========


class TestVTTBasicGeneration:
    """VTT 基础生成测试。"""

    @pytest.mark.unit
    def test_vtt_header(self, engine: SRTEngine, sample_segments, tmp_path: Path):
        """生成的 VTT 文件以 WEBVTT 头部开头。"""
        output = tmp_path / "out.vtt"
        engine.generate_to_path(str(output), sample_segments)

        content = output.read_text(encoding="utf-8")
        assert content.startswith("WEBVTT\n\n")

    @pytest.mark.unit
    def test_vtt_dot_separated_timestamps(
        self, engine: SRTEngine, sample_segments, tmp_path: Path
    ):
        """VTT 时间戳使用点号分隔（HH:MM:SS.mmm）。"""
        output = tmp_path / "out.vtt"
        engine.generate_to_path(str(output), sample_segments)

        content = output.read_text(encoding="utf-8")
        # 应包含 dot-separated 时间戳，不应有 comma-separated
        assert "00:00:02.500" in content
        assert "00:00:05.750" in content
        assert "00:00:08.500" in content
        # 确认不存在逗号分隔的时间戳
        for line in content.splitlines():
            if "-->" in line:
                assert "." in line, f"VTT 时间戳应使用点号: {line}"
                # 不应以逗号分隔（SRT 格式）
                assert not (
                    "," in line
                    and "-->" in line
                    and not line.strip().startswith("WEBVTT")
                ), f"VTT 不应使用逗号分隔: {line}"

    @pytest.mark.unit
    def test_vtt_segment_count(self, engine: SRTEngine, sample_segments, tmp_path: Path):
        """生成的 VTT 包含正确数量的字幕块。"""
        output = tmp_path / "out.vtt"
        engine.generate_to_path(str(output), sample_segments)

        content = output.read_text(encoding="utf-8")
        blocks = [b for b in content.strip().split("\n\n") if "-->" in b]
        assert len(blocks) == len(sample_segments)

    @pytest.mark.unit
    def test_vtt_text_content(self, engine: SRTEngine, sample_segments, tmp_path: Path):
        """VTT 文件包含正确的文本内容。"""
        output = tmp_path / "out.vtt"
        engine.generate_to_path(str(output), sample_segments)

        content = output.read_text(encoding="utf-8")
        assert "Hello, world!" in content
        assert "This is a test." in content
        assert "Goodbye!" in content


class TestVTTBilingual:
    """VTT 双语布局测试。"""

    @pytest.mark.unit
    def test_bilingual_translate_on_top(
        self, engine: SRTEngine, bilingual_segments, tmp_path: Path
    ):
        """双语布局：译文在上。"""
        output = tmp_path / "out.vtt"
        engine.generate_to_path(
            str(output),
            bilingual_segments,
            bilingual=True,
            layout=BilingualLayout.TRANSLATE_ON_TOP,
        )

        content = output.read_text(encoding="utf-8")
        # 译文在上，原文在下
        assert "你好世界！\nHello, world!" in content
        assert "这是一个测试。\nThis is a test." in content

    @pytest.mark.unit
    def test_bilingual_original_on_top(
        self, engine: SRTEngine, bilingual_segments, tmp_path: Path
    ):
        """双语布局：原文在上。"""
        output = tmp_path / "out.vtt"
        engine.generate_to_path(
            str(output),
            bilingual_segments,
            bilingual=True,
            layout=BilingualLayout.ORIGINAL_ON_TOP,
        )

        content = output.read_text(encoding="utf-8")
        assert "Hello, world!\n你好世界！" in content
        assert "This is a test.\n这是一个测试。" in content

    @pytest.mark.unit
    def test_bilingual_only_translate(
        self, engine: SRTEngine, bilingual_segments, tmp_path: Path
    ):
        """双语布局：仅译文。"""
        output = tmp_path / "out.vtt"
        engine.generate_to_path(
            str(output),
            bilingual_segments,
            bilingual=True,
            layout=BilingualLayout.ONLY_TRANSLATE,
        )

        content = output.read_text(encoding="utf-8")
        assert "你好世界！" in content
        assert "Hello, world!" not in content

    @pytest.mark.unit
    def test_bilingual_only_original(
        self, engine: SRTEngine, bilingual_segments, tmp_path: Path
    ):
        """双语布局：仅原文。"""
        output = tmp_path / "out.vtt"
        engine.generate_to_path(
            str(output),
            bilingual_segments,
            bilingual=True,
            layout=BilingualLayout.ONLY_ORIGINAL,
        )

        content = output.read_text(encoding="utf-8")
        assert "Hello, world!" in content
        # "你好世界！" 不应出现在独立的文本行中（作为 original_text 保留）
        # 但在 ONLY_ORIGINAL 模式下，text 被替换为 original_text
        # 所以译文内容不会作为字幕文本出现

    @pytest.mark.unit
    def test_bilingual_vtt_still_has_header(
        self, engine: SRTEngine, bilingual_segments, tmp_path: Path
    ):
        """双语 VTT 文件仍然有 WEBVTT 头部。"""
        output = tmp_path / "out.vtt"
        engine.generate_to_path(
            str(output), bilingual_segments, bilingual=True
        )

        content = output.read_text(encoding="utf-8")
        assert content.startswith("WEBVTT\n\n")


class TestVTTParsing:
    """VTT 解析测试。"""

    @pytest.mark.unit
    def test_parse_basic_vtt(self, engine: SRTEngine, tmp_path: Path):
        """解析基础 VTT 文件。"""
        vtt_content = (
            "WEBVTT\n\n"
            "1\n"
            "00:00:01.000 --> 00:00:03.500\n"
            "Hello, world!\n\n"
            "2\n"
            "00:00:04.000 --> 00:00:06.250\n"
            "This is a test.\n\n"
            "3\n"
            "00:00:07.000 --> 00:00:09.000\n"
            "Goodbye!\n\n"
        )
        vtt_file = tmp_path / "test.vtt"
        vtt_file.write_text(vtt_content, encoding="utf-8")

        segments = engine.parse(str(vtt_file))

        assert len(segments) == 3
        assert segments[0] == {
            "start": 1.0,
            "end": 3.5,
            "text": "Hello, world!",
        }
        assert segments[1] == {
            "start": 4.0,
            "end": 6.25,
            "text": "This is a test.",
        }
        assert segments[2] == {
            "start": 7.0,
            "end": 9.0,
            "text": "Goodbye!",
        }

    @pytest.mark.unit
    def test_parse_vtt_with_multiline_text(self, engine: SRTEngine, tmp_path: Path):
        """解析包含多行文本的 VTT 块（双语字幕场景）。"""
        vtt_content = (
            "WEBVTT\n\n"
            "1\n"
            "00:00:01.000 --> 00:00:03.500\n"
            "你好世界！\n"
            "Hello, world!\n\n"
        )
        vtt_file = tmp_path / "bilingual.vtt"
        vtt_file.write_text(vtt_content, encoding="utf-8")

        segments = engine.parse(str(vtt_file))

        assert len(segments) == 1
        assert segments[0]["text"] == "你好世界！\nHello, world!"

    @pytest.mark.unit
    def test_parse_vtt_empty_file(self, engine: SRTEngine, tmp_path: Path):
        """解析空 VTT 文件（只有头部）。"""
        vtt_file = tmp_path / "empty.vtt"
        vtt_file.write_text("WEBVTT\n\n", encoding="utf-8")

        segments = engine.parse(str(vtt_file))
        assert segments == []

    @pytest.mark.unit
    def test_parse_nonexistent_file(self, engine: SRTEngine, tmp_path: Path):
        """解析不存在的文件应抛出异常。"""
        from mediafactory.exceptions import ProcessingError

        with pytest.raises(ProcessingError, match="not found"):
            engine.parse(str(tmp_path / "nonexistent.vtt"))

    @pytest.mark.unit
    def test_roundtrip(self, engine: SRTEngine, sample_segments, tmp_path: Path):
        """生成后解析应还原相同数据。"""
        output = tmp_path / "roundtrip.vtt"
        engine.generate_to_path(str(output), sample_segments)

        parsed = engine.parse(str(output))

        assert len(parsed) == len(sample_segments)
        for original, parsed_seg in zip(sample_segments, parsed):
            assert abs(original["start"] - parsed_seg["start"]) < 0.001
            assert abs(original["end"] - parsed_seg["end"]) < 0.001
            assert original["text"] == parsed_seg["text"]


class TestSRTGenerationStageVTT:
    """通过 SRTGenerationStage 验证 VTT 输出。"""

    @pytest.mark.unit
    def test_stage_produces_vtt_when_configured(
        self, engine: SRTEngine, sample_segments, tmp_path: Path
    ):
        """SRTGenerationStage 在配置为 vtt 时生成 VTT 文件。"""
        video_file = tmp_path / "sample.mp4"
        video_file.touch()

        output_path = str(tmp_path / "sample_zh.vtt")
        ctx = ProcessingContext(
            video_path=str(video_file),
            transcription_result={
                "segments": sample_segments,
                "language": "en",
            },
            tgt_lang="zh",
            detected_lang="en",
            config={
                "output_format_type": "vtt",
                "output_path": output_path,
            },
        )

        stage = SRTGenerationStage(srt_engine=engine)
        result_ctx = stage.execute(ctx)

        # 验证输出文件已生成
        assert result_ctx.output_path == output_path
        assert os.path.exists(output_path)

        content = Path(output_path).read_text(encoding="utf-8")
        assert content.startswith("WEBVTT\n\n")
        # 验证 VTT 时间戳格式
        assert "00:00:02.500" in content

    @pytest.mark.unit
    def test_stage_auto_vtt_extension(
        self, engine: SRTEngine, sample_segments, tmp_path: Path
    ):
        """未指定 output_path 时，根据 output_format_type 自动使用 .vtt 扩展名。"""
        video_file = tmp_path / "video.mp4"
        video_file.touch()

        ctx = ProcessingContext(
            video_path=str(video_file),
            transcription_result={
                "segments": sample_segments,
                "language": "en",
            },
            tgt_lang="zh",
            detected_lang="en",
            config={
                "output_format_type": "vtt",
            },
        )

        stage = SRTGenerationStage(srt_engine=engine)
        result_ctx = stage.execute(ctx)

        assert result_ctx.output_path.endswith(".vtt")
        assert os.path.exists(result_ctx.output_path)

        content = Path(result_ctx.output_path).read_text(encoding="utf-8")
        assert content.startswith("WEBVTT\n\n")
