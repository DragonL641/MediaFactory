#!/usr/bin/env python3
"""
MediaFactory Windows 构建入口

用法:
    python scripts/build/build_win.py          # 构建
    python scripts/build/build_win.py --clean  # 仅清理
"""

import sys
from pathlib import Path

# 添加 utils 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))

from build_executor import build_windows, clean_build_artifacts


def main():
    import argparse

    parser = argparse.ArgumentParser(description="MediaFactory Windows 构建")
    parser.add_argument("--clean", action="store_true", help="仅清理构建产物")
    parser.add_argument("--version", default=None, help="版本号（默认从 pyproject.toml 读取）")
    args = parser.parse_args()

    if args.clean:
        clean_build_artifacts("windows")
        return 0

    return build_windows(args.version)


if __name__ == "__main__":
    sys.exit(main())
