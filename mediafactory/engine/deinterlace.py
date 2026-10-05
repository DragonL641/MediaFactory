"""Deinterlace 前置修复：FFmpeg idet 检测 + 条件 bwdif 预处理（老片隔行源正确性步骤）"""

import os
import re
import subprocess
from dataclasses import dataclass

from mediafactory.core.progress_protocol import ProgressCallback
from mediafactory.i18n import t
from mediafactory.logging import log_info, log_warning

IDET_SAMPLE_FRAMES = 2000
INTERLACE_THRESHOLD = 0.05  # 隔行帧占比 ≥ 5% 判为隔行源
UNDETERMINED_LIMIT = 0.5  # 不可判定占比过半时视为检测结果不可靠


@dataclass
class DeinterlaceVerdict:
    """idet 检测结论"""

    interlaced: bool
    reliable: bool
    tff: int
    bff: int
    progressive: int
    undetermined: int


_MULTI_RE = re.compile(
    r"Multi frame detection: TFF: (\d+) BFF: (\d+) Progressive: (\d+) Undetermined: (\d+)"
)


def _get_ffmpeg_exe() -> str:
    from imageio_ffmpeg import get_ffmpeg_exe

    return get_ffmpeg_exe()


def parse_idet_output(raw: str, threshold: float = INTERLACE_THRESHOLD) -> DeinterlaceVerdict:
    """解析 idet stderr，取最后一次 Multi frame detection 汇总行判定。"""
    matches = _MULTI_RE.findall(raw)
    if not matches:
        return DeinterlaceVerdict(False, False, 0, 0, 0, 0)
    tff, bff, prog, undet = (int(n) for n in matches[-1])
    total = tff + bff + prog + undet
    reliable = total > 0 and (undet / total) <= UNDETERMINED_LIMIT
    interlaced = reliable and ((tff + bff) / total) >= threshold
    return DeinterlaceVerdict(interlaced, reliable, tff, bff, prog, undet)


def detect_interlaced(
    video_path: str, sample_frames: int = IDET_SAMPLE_FRAMES
) -> DeinterlaceVerdict:
    """对前 sample_frames 帧跑 idet 检测"""
    result = subprocess.run(
        [
            _get_ffmpeg_exe(),
            "-i",
            video_path,
            "-vf",
            "idet",
            "-frames:v",
            str(sample_frames),
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )
    verdict = parse_idet_output(result.stderr)
    log_info(
        f"idet 检测: interlaced={verdict.interlaced}, reliable={verdict.reliable}, "
        f"TFF={verdict.tff}, BFF={verdict.bff}, Progressive={verdict.progressive}, "
        f"Undetermined={verdict.undetermined}"
    )
    return verdict


def build_bwdif_cmd(video_path: str, out_path: str) -> list[str]:
    """bwdif 前置命令：中间产物丢音轨（-an），音频在最终合成时从源取"""
    return [
        _get_ffmpeg_exe(),
        "-i",
        video_path,
        "-vf",
        "bwdif",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-an",
        "-y",
        "-loglevel",
        "error",
        out_path,
    ]


def pre_deinterlace(video_path: str, progress: ProgressCallback | None = None) -> str:
    """隔行源写临时去隔行文件并返回其路径；非隔行/检测失败原样返回。

    检测异常按非隔行降级（宁可跳过不阻断，spec §5）。"""
    try:
        verdict = detect_interlaced(video_path)
    except Exception as e:  # noqa: BLE001
        log_warning(f"idet 检测失败，按非隔行处理: {e}")
        return video_path
    if not verdict.interlaced:
        return video_path
    if progress is not None:
        progress.update(4, t("progress.deinterlacing"))
    out_dir = os.path.join(
        os.path.dirname(video_path) or ".", f".mf_deint_{os.getpid()}"
    )
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "deinterlaced.mp4")
    try:
        result = subprocess.run(
            build_bwdif_cmd(video_path, out_path),
            capture_output=True,
            text=True,
            timeout=3600,
        )
    except Exception as e:  # noqa: BLE001
        log_warning(f"bwdif 前置失败，按非隔行处理: {e}")
        return video_path
    if result.returncode != 0 or not os.path.exists(out_path):
        log_warning(f"bwdif 前置失败，按非隔行处理: {result.stderr[-500:]}")
        return video_path
    log_info(f"deinterlace 前置完成: {out_path}")
    return out_path
