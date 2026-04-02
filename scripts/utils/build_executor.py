#!/usr/bin/env python3
"""
MediaFactory 构建执行器模块

封装 PyInstaller 调用逻辑，供 build_darwin.py / build_win.py 调用。
"""

import os
import shutil
import subprocess
import sys

from datetime import datetime
from pathlib import Path
from typing import List, Optional

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))
from build_common import (
    get_project_root,
    get_project_version,
    log_info,
    log_error,
    log_success,
    log_step,
)

PROJECT_NAME = "MediaFactory"


def run_pyinstaller(version: str, extra_args: Optional[List[str]] = None) -> bool:
    """运行 PyInstaller 构建。

    Args:
        version: 版本号（通过环境变量传递给 spec 文件）
        extra_args: 额外的 PyInstaller 参数

    Returns:
        是否成功
    """
    root = get_project_root()
    spec_file = root / "scripts" / "pyinstaller" / "installer_simple.spec"

    if not spec_file.exists():
        log_error(f"Spec 文件不存在: {spec_file}")
        return False

    os.chdir(root)
    env = os.environ.copy()
    env["APP_VERSION"] = version

    log_info("运行 PyInstaller...")
    cmd = [sys.executable, "-m", "PyInstaller", str(spec_file), "--clean", "--noconfirm"]

    if extra_args:
        cmd.extend(extra_args)

    result = subprocess.run(cmd, env=env)
    return result.returncode == 0


def build_backend(platform_name: str, version: Optional[str] = None) -> int:
    """执行 Python 后端构建（通用，跨平台）。

    流程：PyInstaller 打包 → 复制到 dist/python/（供 electron-builder 使用）

    Args:
        platform_name: 平台显示名称（如 "macOS"、"Windows"）
        version: 版本号（可选，默认从 pyproject.toml 读取）

    Returns:
        退出码（0 表示成功）
    """
    version = version or get_project_version()
    log_step(f"开始构建 {PROJECT_NAME} v{version} ({platform_name})")

    start = datetime.now()

    if not run_pyinstaller(version):
        log_error("PyInstaller 失败")
        return 1

    # 复制 PyInstaller COLLECT 产物到 dist/python/（electron-builder 需要）
    project_root = get_project_root()
    python_dist = project_root / "dist" / "python"
    if python_dist.exists():
        shutil.rmtree(python_dist)
    shutil.copytree(project_root / "dist" / PROJECT_NAME, python_dist)
    log_info(f"已复制到 {python_dist}（用于 Electron 打包）")

    elapsed = (datetime.now() - start).total_seconds()
    log_success(f"构建完成! 耗时: {elapsed:.1f}秒")

    return 0
