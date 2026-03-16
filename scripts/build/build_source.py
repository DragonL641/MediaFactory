#!/usr/bin/env python3
"""
MediaFactory 源码归档构建

用法:
    python scripts/build/build_source.py           # 构建 tar.gz 和 zip
    python scripts/build/build_source.py --zip-only # 仅构建 zip
"""

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 添加 utils 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))

from build_common import (
    get_project_root,
    get_project_version,
    format_file_size,
    log_info,
    log_error,
    log_success,
    log_step,
)


def create_source_archive(zip_only: bool = False) -> int:
    """创建源码归档。

    Args:
        zip_only: 仅创建 zip 文件

    Returns:
        退出码（0 表示成功）
    """
    root = get_project_root()
    version = get_project_version()
    release_dir = root / "release"
    release_dir.mkdir(parents=True, exist_ok=True)

    archive_base = f"MediaFactory-{version}.source"

    log_step(f"创建源码归档 v{version}")

    # 使用 git archive 创建干净的归档
    # 排除 .git 目录和其他不需要的文件

    start = datetime.now()

    # 创建 .tar.gz
    if not zip_only:
        tar_path = release_dir / f"{archive_base}.tar.gz"
        log_info("创建 tar.gz...")
        result = subprocess.run(
            [
                "git", "archive",
                "--format=tar.gz",
                f"--output={tar_path}",
                "HEAD"
            ],
            cwd=root
        )
        if result.returncode != 0:
            log_error("tar.gz 创建失败")
            return 1
        log_info(f"tar.gz: {tar_path.name} ({format_file_size(tar_path.stat().st_size)})")

    # 创建 .zip
    zip_path = release_dir / f"{archive_base}.zip"
    log_info("创建 zip...")
    result = subprocess.run(
        [
            "git", "archive",
            "--format=zip",
            f"--output={zip_path}",
            "HEAD"
        ],
        cwd=root
    )
    if result.returncode != 0:
        log_error("zip 创建失败")
        return 1
    log_info(f"zip: {zip_path.name} ({format_file_size(zip_path.stat().st_size)})")

    elapsed = (datetime.now() - start).total_seconds()
    log_success(f"归档完成! 耗时: {elapsed:.1f}秒")
    log_info(f"输出目录: {release_dir}")

    return 0


def main():
    parser = argparse.ArgumentParser(description="MediaFactory 源码归档")
    parser.add_argument("--zip-only", action="store_true", help="仅创建 zip 文件")
    args = parser.parse_args()

    return create_source_archive(zip_only=args.zip_only)


if __name__ == "__main__":
    sys.exit(main())
