#!/usr/bin/env python3
"""
MediaFactory 构建执行器模块

封装「PyInstaller → 组装 Tauri resources → tauri build」桌面打包全链，
供 build_darwin.py / build_win.py 调用。
"""

import glob
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
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(spec_file),
        "--clean",
        "--noconfirm",
    ]

    if extra_args:
        cmd.extend(extra_args)

    result = subprocess.run(cmd, env=env)
    return result.returncode == 0


def assemble_tauri_backend() -> bool:
    """组装 src-tauri/python-backend/：COLLECT 产物 + webui（daemon 同源伺服所需）。

    daemon 在 frozen 下从可执行文件同级目录找 webui/（get_app_root_dir），
    故 webui 复制到 exe 旁而非打进 spec datas。
    """
    root = get_project_root()
    collect_dir = root / "dist" / PROJECT_NAME
    webui_dir = root / "webui"
    backend_dir = root / "src-tauri" / "python-backend"

    if not collect_dir.is_dir():
        log_error(f"PyInstaller COLLECT 产物不存在: {collect_dir}")
        return False
    if not webui_dir.is_dir():
        log_error("webui/ 不存在——请先运行 `npm run build` 构建前端")
        return False

    if backend_dir.exists():
        shutil.rmtree(backend_dir)
    log_info(f"组装 {backend_dir} ...")
    shutil.copytree(collect_dir, backend_dir)
    shutil.copytree(webui_dir, backend_dir / "webui")
    return True


def run_tauri_build() -> bool:
    """运行 tauri build（产物在 src-tauri/target/release/bundle/）"""
    root = get_project_root()
    npm = shutil.which("npm")
    if npm is None:
        log_error("未找到 npm（桌面打包需要 Node.js >= 20.19.0）")
        return False

    log_info("运行 tauri build（Rust 编译 + bundle，首次较慢）...")
    result = subprocess.run([npm, "run", "tauri", "build"], cwd=root)
    return result.returncode == 0


def collect_bundle_artifacts() -> bool:
    """复制 Tauri bundle 产物（dmg/nsis 安装包）到统一 release/ 目录"""
    root = get_project_root()
    bundle_dir = root / "src-tauri" / "target" / "release" / "bundle"
    release_dir = root / "release"
    release_dir.mkdir(exist_ok=True)

    patterns = ["dmg/*.dmg", "nsis/*.exe"]
    found = []
    for pattern in patterns:
        found.extend(glob.glob(str(bundle_dir / pattern)))

    if not found:
        log_error(f"未在 {bundle_dir} 找到 dmg/nsis 安装包")
        return False

    for path in found:
        dest = release_dir / Path(path).name
        shutil.copy2(path, dest)
        log_info(f"安装包: {dest}")
    return True


def build_desktop(platform_name: str, version: Optional[str] = None) -> int:
    """执行桌面应用全链构建（通用，跨平台）。

    流程：PyInstaller 打包 → 组装 src-tauri/python-backend → tauri build → 收集安装包

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
    if not assemble_tauri_backend():
        return 1
    if not run_tauri_build():
        log_error("tauri build 失败")
        return 1
    if not collect_bundle_artifacts():
        return 1

    elapsed = (datetime.now() - start).total_seconds()
    log_success(f"构建完成! 耗时: {elapsed:.1f}秒")

    return 0
