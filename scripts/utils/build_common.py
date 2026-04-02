#!/usr/bin/env python3
"""
MediaFactory 构建系统公共工具模块

提供版本获取、日志、文件格式化等基础功能。
"""

import os
import sys
from pathlib import Path


# ============================================================================
# 项目信息
# ============================================================================

def get_project_root() -> Path:
    """获取项目根目录"""
    return Path(__file__).parent.parent.parent.resolve()


def get_project_version() -> str:
    """获取项目版本号（统一从 _version.py 获取）"""
    root = get_project_root()
    src_dir = str(root / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    try:
        from mediafactory._version import get_version
        return get_version()
    except Exception:
        pass

    # 最终回退：简单解析 pyproject.toml
    pyproject_path = root / "pyproject.toml"
    try:
        with open(pyproject_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("version = "):
                    version = stripped.split("=", 1)[1].strip().strip("\"'")
                    if version:
                        return version
    except Exception:
        pass

    return "0.0.0"


# ============================================================================
# 日志工具
# ============================================================================

def _is_windows() -> bool:
    """检查是否为 Windows"""
    return sys.platform == "win32"


class BuildLogger:
    """构建日志工具类"""

    COLORS = {
        "SUCCESS": "\033[0;32m",   # 绿色
        "WARN": "\033[0;33m",      # 黄色
        "ERROR": "\033[0;31m",     # 红色
        "STEP": "\033[0;36m",      # 青色
        "RESET": "\033[0m",        # 重置
    }

    def __init__(self, use_colors: bool = True):
        # Windows 控制台设置为 UTF-8 编码，支持中文输出
        if _is_windows():
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            if hasattr(sys.stderr, 'reconfigure'):
                sys.stderr.reconfigure(encoding='utf-8', errors='replace')

        self.use_colors = use_colors and self._supports_color()

    def _supports_color(self) -> bool:
        """检查终端是否支持颜色"""
        if _is_windows() and not os.environ.get("ANSICON"):
            return False
        return True

    def _colorize(self, level: str, message: str) -> str:
        if not self.use_colors:
            return message
        color = self.COLORS.get(level, "")
        return f"{color}{message}{self.COLORS['RESET']}"

    def info(self, message: str):
        print(f"[INFO] {message}")

    def warn(self, message: str):
        colored = self._colorize("WARN", message)
        print(f"[WARN] {colored}")

    def error(self, message: str):
        colored = self._colorize("ERROR", message)
        print(colored, file=sys.stderr)

    def success(self, message: str):
        colored = self._colorize("SUCCESS", message)
        print(colored)

    def step(self, message: str):
        separator = "=" * 60
        colored = self._colorize("STEP", message)
        print(f"\n{separator}")
        print(f"  {colored}")
        print(f"{separator}")


# 全局日志器实例
logger = BuildLogger()


def log_info(msg: str):
    logger.info(msg)

def log_warn(msg: str):
    logger.warn(msg)

def log_error(msg: str):
    logger.error(msg)

def log_success(msg: str):
    logger.success(msg)

def log_step(msg: str):
    logger.step(msg)


# ============================================================================
# 文件工具
# ============================================================================

def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"
