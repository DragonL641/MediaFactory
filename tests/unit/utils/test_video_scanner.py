"""Unit tests for video_scanner module."""

import pytest

from mediafactory.utils.video_scanner import (
    format_file_list,
    is_video_file,
    resolve_input_path,
    scan_video_files,
)

pytestmark = [pytest.mark.unit]


class TestIsVideoFile:
    """Tests for is_video_file()."""

    def test_mp4_supported(self):
        assert is_video_file("movie.mp4") is True

    def test_mkv_supported(self):
        assert is_video_file("film.mkv") is True

    def test_avi_supported(self):
        assert is_video_file("clip.avi") is True

    def test_mov_supported(self):
        assert is_video_file("recording.mov") is True

    def test_wmv_supported(self):
        assert is_video_file("video.wmv") is True

    def test_webm_supported(self):
        assert is_video_file("clip.webm") is True

    def test_txt_not_supported(self):
        assert is_video_file("notes.txt") is False

    def test_pdf_not_supported(self):
        assert is_video_file("doc.pdf") is False

    def test_jpg_not_supported(self):
        assert is_video_file("photo.jpg") is False

    def test_case_insensitive(self):
        assert is_video_file("Movie.MP4") is True
        assert is_video_file("clip.Mkv") is True

    def test_path_object(self):
        from pathlib import Path

        assert is_video_file(Path("/media/video.mp4")) is True
        assert is_video_file(Path("/media/readme.txt")) is False


class TestResolveInputPath:
    """Tests for resolve_input_path()."""

    def test_single_video_file(self, tmp_path):
        """A single video file returns ("file", [path])."""
        video = tmp_path / "demo.mp4"
        video.write_text("fake")
        path_type, files = resolve_input_path(video)
        assert path_type == "file"
        assert len(files) == 1
        assert files[0] == str(video.resolve())

    def test_nonexistent_path_raises(self, tmp_path):
        """Nonexistent path raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="路径不存在"):
            resolve_input_path(tmp_path / "no_such_file.mp4")

    def test_unsupported_format_raises(self, tmp_path):
        """A non-video file raises ValueError."""
        txt = tmp_path / "readme.txt"
        txt.write_text("hello")
        with pytest.raises(ValueError, match="不支持的视频格式"):
            resolve_input_path(txt)

    def test_directory_with_videos(self, tmp_path):
        """A directory with videos returns ("directory", [...])."""
        (tmp_path / "a.mp4").write_text("a")
        (tmp_path / "b.mkv").write_text("b")
        path_type, files = resolve_input_path(tmp_path)
        assert path_type == "directory"
        assert len(files) == 2

    def test_empty_directory_raises(self, tmp_path):
        """An empty directory raises ValueError."""
        subdir = tmp_path / "empty"
        subdir.mkdir()
        with pytest.raises(ValueError, match="没有找到视频文件"):
            resolve_input_path(subdir)

    def test_directory_with_no_videos_raises(self, tmp_path):
        """A directory that only has non-video files raises ValueError."""
        (tmp_path / "notes.txt").write_text("notes")
        (tmp_path / "image.jpg").write_text("img")
        with pytest.raises(ValueError, match="没有找到视频文件"):
            resolve_input_path(tmp_path)


class TestScanVideoFiles:
    """Tests for scan_video_files()."""

    def test_empty_directory(self, tmp_path):
        """Empty directory returns empty list."""
        empty = tmp_path / "empty"
        empty.mkdir()
        assert scan_video_files(empty) == []

    def test_nonexistent_directory(self, tmp_path):
        """Nonexistent directory returns empty list."""
        assert scan_video_files(tmp_path / "nope") == []

    def test_finds_video_files(self, tmp_path):
        """Finds video files in a flat directory."""
        (tmp_path / "alpha.mp4").write_text("a")
        (tmp_path / "beta.mkv").write_text("b")
        (tmp_path / "readme.txt").write_text("skip")
        files = scan_video_files(tmp_path, recursive=False)
        assert len(files) == 2
        # Sorted by filename (case-insensitive)
        names = [__import__("pathlib").Path(f).name for f in files]
        assert names == ["alpha.mp4", "beta.mkv"]

    def test_recursive_scan(self, tmp_path):
        """Recursive scan finds videos in subdirectories."""
        sub = tmp_path / "subdir"
        sub.mkdir()
        (tmp_path / "top.mp4").write_text("t")
        (sub / "nested.avi").write_text("n")
        files = scan_video_files(tmp_path, recursive=True)
        assert len(files) == 2
        names = [__import__("pathlib").Path(f).name for f in files]
        assert "nested.avi" in names
        assert "top.mp4" in names

    def test_non_recursive_skips_subdirs(self, tmp_path):
        """Non-recursive scan skips subdirectories."""
        sub = tmp_path / "subdir"
        sub.mkdir()
        (tmp_path / "top.mp4").write_text("t")
        (sub / "nested.avi").write_text("n")
        files = scan_video_files(tmp_path, recursive=False)
        assert len(files) == 1
        assert files[0].endswith("top.mp4")

    def test_results_sorted_by_name(self, tmp_path):
        """Results are sorted by filename (case-insensitive)."""
        for name in ["c.mp4", "B.mkv", "a.avi"]:
            (tmp_path / name).write_text("x")
        files = scan_video_files(tmp_path, recursive=False)
        names = [__import__("pathlib").Path(f).name for f in files]
        assert names == ["a.avi", "B.mkv", "c.mp4"]


class TestFormatFileList:
    """Tests for format_file_list()."""

    def test_empty_list(self):
        """Empty list returns placeholder text."""
        result = format_file_list([])
        assert "无视频文件" in result

    def test_short_list(self):
        """A short list shows all entries with numbered brackets."""
        files = ["/a.mp4", "/b.mkv"]
        result = format_file_list(files)
        assert "[  1] /a.mp4" in result
        assert "[  2] /b.mkv" in result

    def test_truncation_with_max_display(self):
        """List longer than max_display is truncated with a summary line."""
        files = [f"/video_{i}.mp4" for i in range(10)]
        result = format_file_list(files, max_display=5)
        # Should show first 5 entries
        assert "[  1] /video_0.mp4" in result
        assert "[  5] /video_4.mp4" in result
        # Should NOT show the 6th entry
        assert "video_5.mp4" not in result
        # Should show truncation message
        assert "5 个更多文件" in result

    def test_exactly_max_display(self):
        """List exactly at max_display shows all entries without truncation."""
        files = [f"/v{i}.mp4" for i in range(3)]
        result = format_file_list(files, max_display=3)
        assert "更多文件" not in result
