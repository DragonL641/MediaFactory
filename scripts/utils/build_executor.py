#!/usr/bin/env python3
"""
MediaFactory 构建执行器模块

封装 PyInstaller 调用的通用逻辑，减少 build_darwin.py 和 build_win.py 的代码重复。
"""

import os
import platform
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))
from build_common import (
    get_project_root,
    get_project_version,
    format_file_size,
    log_info,
    log_warn,
    log_error,
    log_success,
    log_step,
)

PROJECT_NAME = "MediaFactory"

# Inno Setup AppId（固定 GUID，用于升级安装识别）
MEDIAFACTORY_APP_ID = "A7B3C8D2-E4F1-4A9E-8B5C-2D1F3E9A6C7B"


def run_pyinstaller(version: str, extra_args: Optional[List[str]] = None) -> bool:
    """运行 PyInstaller 构建。

    Args:
        version: 版本号（用于环境变量）
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


def create_zip_archive(version: str) -> bool:
    """创建 .app.zip 分发包（macOS）。

    Args:
        version: 版本号

    Returns:
        是否成功
    """
    root = get_project_root()
    dist_dir = root / "dist"
    app_path = dist_dir / f"{PROJECT_NAME}.app"
    zip_path = dist_dir / f"{PROJECT_NAME}-{version}.app.zip"

    if not app_path.exists():
        log_error(f".app 不存在: {app_path}")
        return False

    if zip_path.exists():
        zip_path.unlink()

    log_info("创建 ZIP 分发包...")
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file in app_path.rglob('*'):
                if file.is_file() and '__pycache__' not in str(file):
                    zf.write(file, file.relative_to(app_path.parent))

        size = zip_path.stat().st_size
        log_info(f"ZIP: {zip_path.name} ({format_file_size(size)})")
        return True
    except Exception as e:
        log_error(f"ZIP 创建失败: {e}")
        return False


def run_inno_setup(version: str) -> bool:
    """运行 Inno Setup 创建安装程序（Windows）。

    Args:
        version: 版本号

    Returns:
        是否成功
    """
    root = get_project_root()
    dist_dir = root / "dist"

    # 检查构建产物：onefile 模式输出单个 exe，onedir 模式输出目录
    onefile_exe = dist_dir / f"{PROJECT_NAME}.exe"
    onedir_path = dist_dir / PROJECT_NAME

    if onefile_exe.exists():
        # onefile 模式：单个 exe 文件
        source_pattern = str(onefile_exe)
        exe_path = f"{{app}}\\{PROJECT_NAME}.exe"
        log_info("检测到 onefile 模式")
    elif onedir_path.exists():
        # onedir 模式：目录
        source_pattern = f"{onedir_path}\\*"
        exe_path = f"{{app}}\\{PROJECT_NAME}\\{PROJECT_NAME}.exe"
        log_info("检测到 onedir 模式")
    else:
        log_error(f"未找到构建产物: {onefile_exe} 或 {onedir_path}")
        return False

    # 检查 iscc 命令是否存在
    if shutil.which("iscc") is None:
        log_warn("Inno Setup 未安装，跳过安装程序创建")
        log_info("可执行文件已生成，可手动分发")
        return True

    # 生成 .iss 配置
    iss_content = f"""[Setup]
AppId={MEDIAFACTORY_APP_ID}
AppName={PROJECT_NAME}
AppVersion={version}
DefaultDirName={{autopf}}\\{PROJECT_NAME}
DefaultGroupName={PROJECT_NAME}
OutputDir={dist_dir}
OutputBaseFilename={PROJECT_NAME}-Setup-{version}
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "{source_pattern}"; DestDir: "{{app}}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{{group}}\\{PROJECT_NAME}"; Filename: "{exe_path}"
Name: "{{autodesktop}}\\{PROJECT_NAME}"; Filename: "{exe_path}"

[Run]
Filename: "{exe_path}"; Description: "启动 {PROJECT_NAME}"; Flags: nowait postinstall
"""

    iss_path = root / "build" / "setup.iss"
    iss_path.parent.mkdir(parents=True, exist_ok=True)
    iss_path.write_text(iss_content, encoding="utf-8")

    log_info("运行 Inno Setup...")
    result = subprocess.run(["iscc", str(iss_path)], cwd=root)
    return result.returncode == 0


def clean_build_artifacts(platform_name: str) -> None:
    """清理构建产物。

    Args:
        platform_name: 平台名称 ("darwin" 或 "windows")
    """
    root = get_project_root()
    dirs_to_clean = [
        root / "build",
        root / "dist" / PROJECT_NAME,
    ]

    if platform_name == "darwin":
        dirs_to_clean.append(root / "dist" / f"{PROJECT_NAME}.app")
    elif platform_name == "windows":
        exe_path = root / "dist" / f"{PROJECT_NAME}.exe"
        if exe_path.exists():
            exe_path.unlink()
            log_info(f"已清理: {exe_path}")

    for d in dirs_to_clean:
        if d.exists():
            shutil.rmtree(d)
            log_info(f"已清理: {d}")


def build_macos(version: Optional[str] = None) -> int:
    """执行 macOS 构建。

    Args:
        version: 版本号（可选，默认从 pyproject.toml 读取）

    Returns:
        退出码（0 表示成功）
    """
    if platform.system() != "Darwin":
        log_error("此脚本仅在 macOS 上运行")
        return 1

    version = version or get_project_version()
    log_step(f"开始构建 {PROJECT_NAME} v{version} (macOS)")

    start = datetime.now()

    if not run_pyinstaller(version):
        log_error("PyInstaller 失败")
        return 1

    if not create_zip_archive(version):
        log_error("ZIP 创建失败")
        return 1

    elapsed = (datetime.now() - start).total_seconds()
    log_success(f"构建完成! 耗时: {elapsed:.1f}秒")
    log_info(f"输出: dist/{PROJECT_NAME}-{version}.app.zip")

    return 0


def build_windows(version: Optional[str] = None) -> int:
    """执行 Windows 构建。

    Args:
        version: 版本号（可选，默认从 pyproject.toml 读取）

    Returns:
        退出码（0 表示成功）
    """
    if platform.system() != "Windows":
        log_error("此脚本仅在 Windows 上运行")
        return 1

    version = version or get_project_version()
    log_step(f"开始构建 {PROJECT_NAME} v{version} (Windows)")

    start = datetime.now()

    if not run_pyinstaller(version):
        log_error("PyInstaller 失败")
        return 1

    if not run_inno_setup(version):
        log_error("Inno Setup 失败")
        return 1

    elapsed = (datetime.now() - start).total_seconds()
    log_success(f"构建完成! 耗时: {elapsed:.1f}秒")
    log_info(f"输出: dist/{PROJECT_NAME}-Setup-{version}.exe")

    return 0


# ============================================================================
# 主模块测试
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=f"{PROJECT_NAME} 构建执行器")
    parser.add_argument("--version", default=None, help="版本号")
    parser.add_argument("--clean", action="store_true", help="仅清理")
    args = parser.parse_args()

    if args.clean:
        current_platform = platform.system().lower()
        if current_platform == "darwin":
            clean_build_artifacts("darwin")
        elif current_platform == "windows":
            clean_build_artifacts("windows")
        else:
            log_warn(f"不支持的平台: {current_platform}")
        sys.exit(0)

    # 根据平台执行构建
    if platform.system() == "Darwin":
        sys.exit(build_macos(args.version))
    elif platform.system() == "Windows":
        sys.exit(build_windows(args.version))
    else:
        log_error(f"不支持的平台: {platform.system()}")
        sys.exit(1)
