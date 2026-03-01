"""
MediaFactory 启动器

检测是否首次运行，启动主应用。
"""

import sys
from pathlib import Path
from typing import Optional


def get_project_root() -> Path:
    """获取项目根目录"""
    if getattr(sys, "frozen", False):
        # 冻结状态（PyInstaller 等）
        return Path(sys.executable).parent
    else:
        # 开发状态
        return Path(__file__).parent.parent.parent


# 首次运行标记文件
FIRST_RUN_MARKER = ".first_run_completed"


def is_first_run(project_root: Optional[Path] = None) -> bool:
    """检测是否首次运行"""
    if project_root is None:
        project_root = get_project_root()
    marker_file = project_root / FIRST_RUN_MARKER
    return not marker_file.exists()


def mark_first_run_completed(project_root: Optional[Path] = None) -> None:
    """标记首次运行完成"""
    if project_root is None:
        project_root = get_project_root()
    marker_file = project_root / FIRST_RUN_MARKER
    marker_file.touch()


def check_dependencies_installed() -> bool:
    """检查 ML 依赖是否已安装"""
    try:
        import torch
        import transformers
        import faster_whisper

        return True
    except ImportError:
        return False


def check_models_downloaded(project_root: Optional[Path] = None) -> bool:
    """检查模型是否已下载"""
    if project_root is None:
        project_root = get_project_root()
    models_dir = project_root / "models"
    if not models_dir.exists():
        return False
    return any(models_dir.iterdir())


def launch_main_application() -> int:
    """启动主应用"""
    try:
        from mediafactory.gui.flet import launch_gui

        launch_gui()
        return 0
    except Exception as e:
        print(f"启动应用失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


def main() -> int:
    """主入口"""
    project_root = get_project_root()

    # 检查模型（可选警告）
    if not check_models_downloaded(project_root):
        print("提示: 未检测到模型，部分功能可能不可用")

    # 检查 ML 依赖（可选警告）
    if not check_dependencies_installed():
        print("提示: 未检测到 ML 依赖，部分功能可能不可用")

    # 启动主应用
    return launch_main_application()


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "get_project_root",
    "is_first_run",
    "mark_first_run_completed",
    "check_dependencies_installed",
    "check_models_downloaded",
    "launch_main_application",
    "main",
]
