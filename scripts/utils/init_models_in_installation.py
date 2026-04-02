#!/usr/bin/env python3
"""
MediaFactory 模型下载脚本（跨平台）

支持 Windows 和 macOS，用于在安装过程中下载 AI 模型。

命令行参数:
    --whisper=<size>   Whisper 模型大小 (small|medium|large-v3)，默认 medium
    --install-dir=<path> 安装目录
    --source=<url>     下载源 (https://huggingface.co 或 https://hf-mirror.com)
    --quiet            静默模式，减少输出
    --progress-file=<path> 将进度写入文件（供安装程序读取）

环境变量 (优先级低于命令行参数):
    WHISPER_MODEL      Whisper 模型大小
    INSTALL_DIR        安装目录
    DOWNLOAD_SOURCE    下载源
    PROGRESS_FILE      进度文件路径

退出码:
    0: 成功
    1: 失败
    2: 用户取消
"""

import os
import sys
import argparse
import platform
from pathlib import Path
from typing import Optional

# 添加项目根目录到 Python 路径
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))


# ============================================================================
# 模型配置
# ============================================================================

WHISPER_MODELS = {
    "small": {
        "model_id": "Systran/faster-whisper-small",
        "alias": "small",
        "size_gb": 0.46,
        "memory_gb": 1.0,
        "display_name": "Whisper Small (460MB)",
    },
    "medium": {
        "model_id": "Systran/faster-whisper-medium",
        "alias": "medium",
        "size_gb": 1.5,
        "memory_gb": 2.5,
        "display_name": "Whisper Medium (1.5GB) - 推荐",
    },
    "large-v3": {
        "model_id": "Systran/faster-whisper-large-v3",
        "alias": "large-v3",
        "size_gb": 3.0,
        "memory_gb": 5.0,
        "display_name": "Whisper Large V3 (3GB) - 最高精度",
    },
}

TRANSLATION_MODEL = {
    "model_id": "facebook/nllb-200-distilled-600M",
    "alias": "nllb-600m",
    "size_gb": 2.4,
    "display_name": "NLLB-600M (翻译)",
}


# ============================================================================
# 平台特定配置
# ============================================================================

def get_default_install_dir() -> Path:
    """获取默认安装目录（跨平台）"""
    system = platform.system()

    if system == "Windows":
        return Path.home() / "MediaFactory"
    elif system == "Darwin":  # macOS
        return Path("/Applications/MediaFactory.app")
    else:  # Linux
        return Path.home() / "MediaFactory"


def get_models_dir(install_dir: Path) -> Path:
    """获取模型目录（跨平台）"""
    system = platform.system()

    if system == "Darwin":  # macOS - 使用应用内目录
        return install_dir / "Contents" / "MacOS" / "models"
    else:
        return install_dir / "models"


def get_cache_dir(install_dir: Path) -> Path:
    """获取缓存目录（跨平台）"""
    system = platform.system()

    if system == "Darwin":  # macOS
        return install_dir / "Contents" / "MacOS" / "cache"
    else:
        return install_dir / "cache"


def get_logs_dir(install_dir: Path) -> Path:
    """获取日志目录（跨平台）"""
    system = platform.system()

    if system == "Darwin":  # macOS
        return install_dir / "Contents" / "MacOS" / "logs"
    else:
        return install_dir / "logs"


# ============================================================================
# 进度输出
# ============================================================================

def print_progress(percent: int, message: str, quiet: bool = False, progress_file: Optional[Path] = None):
    """打印进度信息

    Args:
        percent: 进度百分比 (0-100)
        message: 进度消息
        quiet: 是否静默模式
        progress_file: 进度文件路径（供外部程序读取）
    """
    if not quiet:
        print(f"[{percent:3d}%] {message}")

    if progress_file:
        try:
            progress_file.write_text(f"{percent}|{message}\n", encoding="utf-8")
        except Exception:
            pass  # 忽略文件写入错误


# ============================================================================
# 下载函数
# ============================================================================

def download_whisper_model(
    model_size: str,
    install_dir: Path,
    source: str,
    quiet: bool,
    progress_file: Optional[Path],
) -> bool:
    """下载 Whisper 模型

    Args:
        model_size: 模型大小 (small|medium|large-v3)
        install_dir: 安装目录
        source: 下载源
        quiet: 静默模式
        progress_file: 进度文件

    Returns:
        是否成功
    """
    if model_size not in WHISPER_MODELS:
        print(f"错误: 不支持的模型大小 '{model_size}'")
        return False

    model_config = WHISPER_MODELS[model_size]
    models_dir = get_models_dir(install_dir)
    model_path = models_dir / f"whisper-{model_config['alias']}"

    # 检查是否已存在
    if model_path.exists() and any(model_path.iterdir()):
        print_progress(0, f"Whisper 模型已存在，跳过下载", quiet, progress_file)
        return True

    try:
        from mediafactory.models.model_download import download_model

        def progress_callback(percent: float, message: str = ""):
            # 映射到 0-50% 范围
            adjusted_percent = int(percent * 50)
            print_progress(adjusted_percent, message, quiet, progress_file)

        print_progress(0, f"正在下载 {model_config['display_name']}...", quiet, progress_file)

        download_model(
            model_config["model_id"],
            download_source=source,
            progress_callback=progress_callback,
        )

        print_progress(50, f"Whisper 模型下载完成", quiet, progress_file)
        return True

    except Exception as e:
        print_progress(0, f"Whisper 模型下载失败: {e}", quiet, progress_file)
        return False


def download_translation_model(
    install_dir: Path,
    source: str,
    quiet: bool,
    progress_file: Optional[Path],
) -> bool:
    """下载翻译模型

    Args:
        install_dir: 安装目录
        source: 下载源
        quiet: 静默模式
        progress_file: 进度文件

    Returns:
        是否成功
    """
    model_config = TRANSLATION_MODEL
    models_dir = get_models_dir(install_dir)
    model_path = models_dir / model_config["model_id"].replace("/", "_")

    # 检查是否已存在
    if model_path.exists() and any(model_path.iterdir()):
        print_progress(50, f"翻译模型已存在，跳过下载", quiet, progress_file)
        return True

    try:
        from mediafactory.models.model_download import download_model

        def progress_callback(percent: float, message: str = ""):
            # 映射到 50-100% 范围
            adjusted_percent = 50 + int(percent * 50)
            print_progress(adjusted_percent, message, quiet, progress_file)

        print_progress(50, f"正在下载 {model_config['display_name']}...", quiet, progress_file)

        download_model(
            model_config["model_id"],
            download_source=source,
            progress_callback=progress_callback,
        )

        print_progress(100, f"翻译模型下载完成", quiet, progress_file)
        return True

    except Exception as e:
        print_progress(50, f"翻译模型下载失败: {e}", quiet, progress_file)
        return False


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    # 从环境变量获取默认值
    default_whisper = os.getenv("WHISPER_MODEL", "medium")
    default_install_dir = os.getenv("INSTALL_DIR", str(get_default_install_dir()))
    default_source = os.getenv("DOWNLOAD_SOURCE", "https://hf-mirror.com")
    default_progress_file = os.getenv("PROGRESS_FILE")

    parser = argparse.ArgumentParser(
        description="MediaFactory 模型下载脚本（跨平台）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--whisper",
        choices=["small", "medium", "large-v3"],
        default=default_whisper,
        help="Whisper 模型大小（默认: %(default)s）",
    )
    parser.add_argument(
        "--install-dir",
        type=Path,
        default=Path(default_install_dir),
        help="安装目录",
    )
    parser.add_argument(
        "--source",
        default=default_source,
        help="下载源（默认: %(default)s）",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="静默模式",
    )
    parser.add_argument(
        "--progress-file",
        type=Path,
        default=default_progress_file,
        help="进度文件路径",
    )

    args = parser.parse_args()

    # 创建必要的目录
    args.install_dir.mkdir(parents=True, exist_ok=True)
    get_models_dir(args.install_dir).mkdir(parents=True, exist_ok=True)
    get_cache_dir(args.install_dir).mkdir(parents=True, exist_ok=True)
    logs_dir = get_logs_dir(args.install_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    if not args.quiet:
        print("=" * 60)
        print("MediaFactory 模型下载")
        print("=" * 60)
        print(f"平台: {platform.system()}")
        print(f"Whisper 模型: {WHISPER_MODELS[args.whisper]['display_name']}")
        print(f"翻译模型: {TRANSLATION_MODEL['display_name']}")
        print(f"安装目录: {args.install_dir}")
        print(f"下载源: {args.source}")
        print("=" * 60)
        print()

    # 下载 Whisper 模型
    if not download_whisper_model(
        args.whisper,
        args.install_dir,
        args.source,
        args.quiet,
        args.progress_file,
    ):
        if not args.quiet:
            print("\n错误: Whisper 模型下载失败")
        return 1

    # 下载翻译模型
    if not download_translation_model(
        args.install_dir,
        args.source,
        args.quiet,
        args.progress_file,
    ):
        if not args.quiet:
            print("\n警告: 翻译模型下载失败")
        # 翻译模型失败不是致命错误，继续

    if not args.quiet:
        print()
        print("=" * 60)
        print("模型下载完成！")
        print("=" * 60)
        print(f"Whisper 模型: {WHISPER_MODELS[args.whisper]['display_name']}")
        print(f"翻译模型: {TRANSLATION_MODEL['display_name']}")
        print()
        print("现在可以启动 MediaFactory 开始使用了！")

    return 0


if __name__ == "__main__":
    sys.exit(main())
