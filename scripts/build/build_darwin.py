#!/usr/bin/env python3
"""
MediaFactory macOS 构建入口

用法:
    python scripts/build/build_darwin.py          # 构建
"""

import sys
from pathlib import Path

# 添加 utils 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))

from build_executor import build_backend


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MediaFactory macOS 构建")
    parser.add_argument("--version", default=None, help="版本号（默认从 pyproject.toml 读取）")
    args = parser.parse_args()

    sys.exit(build_backend("macOS", args.version))
