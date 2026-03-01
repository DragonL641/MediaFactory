"""视频文件扫描工具模块。

提供路径解析和视频文件扫描功能，支持单文件和目录批量扫描。
"""

import os
from pathlib import Path
from typing import List, Tuple, Union

from ..constants import FileConstants

# 使用统一的常量定义
SUPPORTED_VIDEO_EXTENSIONS = FileConstants.SUPPORTED_VIDEO_EXTENSIONS


def is_video_file(path: Union[str, Path]) -> bool:
    """检查文件是否为支持的视频格式。

    Args:
        path: 文件路径

    Returns:
        如果是支持的视频格式返回 True，否则返回 False
    """
    path = Path(path)
    return path.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS


def scan_video_files(directory: Union[str, Path], recursive: bool = True) -> List[str]:
    """扫描目录中的所有视频文件。

    Args:
        directory: 目录路径
        recursive: 是否递归扫描子目录，默认为 True

    Returns:
        视频文件路径列表（按文件名排序）
    """
    directory = Path(directory)
    if not directory.is_dir():
        return []

    video_files = []

    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = Path(root) / file
                if is_video_file(file_path):
                    video_files.append(str(file_path.resolve()))
    else:
        for file in directory.iterdir():
            if file.is_file() and is_video_file(file):
                video_files.append(str(file.resolve()))

    # 按文件名排序
    video_files.sort(key=lambda x: Path(x).name.lower())
    return video_files


def resolve_input_path(input_path: Union[str, Path]) -> Tuple[str, List[str]]:
    """解析输入路径，返回路径类型和视频文件列表。

    自动识别输入路径类型（文件或目录）：
    - 若为目录，递归扫描所有视频文件
    - 若为文件，验证是否为支持的视频格式

    Args:
        input_path: 输入路径（文件或目录）

    Returns:
        Tuple[path_type, video_files]:
            - path_type: "file" 或 "directory"
            - video_files: 视频文件路径列表

    Raises:
        FileNotFoundError: 路径不存在
        ValueError: 文件格式不支持或目录中没有视频文件
    """
    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"路径不存在: {input_path}")

    if input_path.is_file():
        if not is_video_file(input_path):
            raise ValueError(
                f"不支持的视频格式: {input_path.suffix}。"
                f"支持的格式: {', '.join(sorted(SUPPORTED_VIDEO_EXTENSIONS))}"
            )
        return "file", [str(input_path.resolve())]

    if input_path.is_dir():
        video_files = scan_video_files(input_path, recursive=True)
        if not video_files:
            raise ValueError(
                f"目录中没有找到视频文件: {input_path}。"
                f"支持的格式: {', '.join(sorted(SUPPORTED_VIDEO_EXTENSIONS))}"
            )
        return "directory", video_files

    raise ValueError(f"无效的路径类型: {input_path}")


def format_file_list(video_files: List[str], max_display: int = 50) -> str:
    """格式化视频文件列表用于显示。

    Args:
        video_files: 视频文件路径列表
        max_display: 最大显示数量，超过则截断

    Returns:
        格式化的文件列表字符串
    """
    if not video_files:
        return "（无视频文件）"

    lines = []
    total = len(video_files)
    display_count = min(total, max_display)

    for i, file_path in enumerate(video_files[:display_count], 1):
        # 显示编号和文件路径
        lines.append(f"  [{i:3d}] {file_path}")

    if total > max_display:
        lines.append(f"  ... 以及 {total - max_display} 个更多文件")

    return "\n".join(lines)


def get_file_size_info(video_files: List[str]) -> Tuple[int, float]:
    """获取文件列表的总大小信息。

    Args:
        video_files: 视频文件路径列表

    Returns:
        Tuple[file_count, total_size_gb]: 文件数量和总大小（GB）
    """
    total_size = 0
    for file_path in video_files:
        try:
            total_size += os.path.getsize(file_path)
        except OSError:
            pass

    return len(video_files), total_size / (1024**3)
