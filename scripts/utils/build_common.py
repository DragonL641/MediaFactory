#!/usr/bin/env python3
"""
MediaFactory 构建系统公共工具模块

提取所有构建脚本中共享的功能，减少代码重复。
"""

import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# tomli 用于解析 TOML 文件（Python < 3.11 需要，>= 3.11 可使用 tomllib）
try:
    import tomli
except ImportError:
    try:
        import tomllib as tomli  # Python 3.11+
    except ImportError:
        tomli = None


# ============================================================================
# 项目信息
# ============================================================================

def get_project_root() -> Path:
    """获取项目根目录"""
    return Path(__file__).parent.parent.parent.resolve()


def get_project_version() -> str:
    """获取项目版本号（使用 tomli 解析 pyproject.toml）"""
    root = get_project_root()
    pyproject_path = root / "pyproject.toml"

    # 优先使用 tomli 库解析
    if tomli is not None:
        try:
            with open(pyproject_path, "rb") as f:
                data = tomli.load(f)
            version = data.get("project", {}).get("version", "")

            # 验证版本号格式 (major.minor.patch[-prerelease])
            if version and re.match(r'^\d+\.\d+\.\d+(?:[a-z]+\.\d+)?$', version):
                return version

            log_warn(f"版本号格式无效: {version}")
        except Exception as e:
            log_warn(f"使用 tomli 解析版本失败: {e}")

    # 回退：简单字符串解析
    try:
        with open(pyproject_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("version = "):
                    version = stripped.split("=", 1)[1].strip().strip("\"'")
                    if version:
                        return version
    except Exception as e:
        log_warn(f"字符串解析版本失败: {e}")

    return "0.0.0"


def get_project_metadata() -> dict:
    """获取完整的项目元数据"""
    return {
        "name": "MediaFactory",
        "version": get_project_version(),
        "root": get_project_root(),
    }


# ============================================================================
# 平台检测
# ============================================================================

def get_platform_name() -> str:
    """获取平台名称 (macos, windows, linux)"""
    system = platform.system().lower()
    return {
        "darwin": "macos",
        "windows": "windows",
        "linux": "linux",
    }.get(system, "unknown")


def get_architecture() -> str:
    """获取系统架构 (x64, arm64)"""
    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        return "arm64"
    elif machine in ("x86_64", "amd64"):
        return "x64"
    return machine


def get_platform_identifier() -> str:
    """获取完整的平台标识符 (例如: macos-x64, windows-x64)"""
    return f"{get_platform_name()}-{get_architecture()}"


def is_macos() -> bool:
    """检查是否为 macOS"""
    return platform.system() == "Darwin"


def is_windows() -> bool:
    """检查是否为 Windows"""
    return platform.system() == "Windows"


def is_linux() -> bool:
    """检查是否为 Linux"""
    return platform.system() == "Linux"


# ============================================================================
# 日志工具
# ============================================================================

class BuildLogger:
    """构建日志工具类"""

    COLORS = {
        "INFO": "\033[0;32m",      # 绿色
        "SUCCESS": "\033[0;32m",   # 绿色
        "WARN": "\033[0;33m",      # 黄色
        "ERROR": "\033[0;31m",     # 红色
        "STEP": "\033[0;36m",      # 青色
        "RESET": "\033[0m",        # 重置
        "NOCOLOR": "",             # 无颜色
    }

    def __init__(self, use_colors: bool = True):
        """初始化日志器

        Args:
            use_colors: 是否使用颜色（Windows cmd 不支持 ANSI 颜色）
        """
        # Windows 控制台设置为 UTF-8 编码，支持中文输出
        if is_windows():
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            if hasattr(sys.stderr, 'reconfigure'):
                sys.stderr.reconfigure(encoding='utf-8', errors='replace')

        self.use_colors = use_colors and self._supports_color()

    def _supports_color(self) -> bool:
        """检查终端是否支持颜色"""
        # Windows cmd 不支持 ANSI 颜色
        if is_windows() and not os.environ.get("ANSICON"):
            return False
        return True

    def _colorize(self, level: str, message: str) -> str:
        """给消息添加颜色"""
        if not self.use_colors:
            return message

        color = self.COLORS.get(level, "")
        return f"{color}{message}{self.COLORS['RESET']}"

    def info(self, message: str):
        """输出信息日志"""
        print(f"[INFO] {message}")

    def warn(self, message: str):
        """输出警告日志"""
        colored = self._colorize("WARN", message)
        print(f"[WARN] {colored}")

    def error(self, message: str):
        """输出错误日志"""
        colored = self._colorize("ERROR", message)
        print(colored, file=sys.stderr)

    def success(self, message: str):
        """输出成功日志"""
        colored = self._colorize("SUCCESS", message)
        print(colored)

    def step(self, message: str):
        """输出步骤标题"""
        separator = "=" * 60
        colored = self._colorize("STEP", message)
        print(f"\n{separator}")
        print(f"  {colored}")
        print(f"{separator}")

    def header(self, title: str):
        """输出标题"""
        separator = "=" * 60
        print(f"\n{separator}")
        print(f"  {title}")
        print(f"{separator}")


# 创建全局日志器实例
logger = BuildLogger()


# 向后兼容的函数别名
def log_info(msg: str):
    """输出信息日志（向后兼容）"""
    logger.info(msg)


def log_warn(msg: str):
    """输出警告日志（向后兼容）"""
    logger.warn(msg)


def log_error(msg: str):
    """输出错误日志（向后兼容）"""
    logger.error(msg)


def log_success(msg: str):
    """输出成功日志（向后兼容）"""
    logger.success(msg)


def log_step(msg: str):
    """输出步骤日志（向后兼容）"""
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


def ensure_directory(path: Path) -> bool:
    """确保目录存在"""
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        log_error(f"无法创建目录 {path}: {e}")
        return False


def get_file_size(path: Path) -> int:
    """获取文件大小"""
    try:
        return path.stat().st_size
    except Exception:
        return 0


# ============================================================================
# 构建目录管理
# ============================================================================

BUILD_DIRS = ["build", "dist", "release"]


def clean_build_artifacts(root: Optional[Path] = None) -> bool:
    """清理构建产物

    Args:
        root: 项目根目录，默认为自动检测

    Returns:
        是否成功
    """
    if root is None:
        root = get_project_root()

    cleaned = 0
    for dir_name in BUILD_DIRS:
        dir_path = root / dir_name
        if dir_path.exists():
            import shutil
            shutil.rmtree(dir_path)
            log_info(f"已清理: {dir_name}/")
            cleaned += 1

    if cleaned > 0:
        log_success("构建产物已清理")
        return True
    return False


def get_build_dirs(root: Optional[Path] = None) -> dict:
    """获取构建目录字典

    Returns:
        {"build": Path, "dist": Path, "release": Path}
    """
    if root is None:
        root = get_project_root()

    return {
        "build": root / "build",
        "dist": root / "dist",
        "release": root / "release",
    }


def ensure_build_dirs(root: Optional[Path] = None) -> bool:
    """确保构建目录存在"""
    if root is None:
        root = get_project_root()

    success = True
    for dir_name in BUILD_DIRS:
        if not ensure_directory(root / dir_name):
            success = False

    return success


# ============================================================================
# 命令执行工具
# ============================================================================

def run_command(
    cmd: list,
    cwd: Optional[Path] = None,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """运行命令并返回结果

    Args:
        cmd: 命令列表
        cwd: 工作目录
        check: 是否检查返回码

    Returns:
        subprocess.CompletedProcess
    """
    if cwd is None:
        cwd = get_project_root()

    cmd_str = " ".join(str(c) for c in cmd[:5]) + " [...]" if len(cmd) > 5 else " ".join(str(c) for c in cmd)
    log_info(f"运行: {cmd_str}")

    result = subprocess.run(
        cmd,
        cwd=cwd,
        check=check,
        stdout=None,  # 继承父进程的 stdout
        stderr=None,  # 继承父进程的 stderr
    )

    if check and result.returncode != 0:
        log_error(f"命令失败 (退出码: {result.returncode})")
    else:
        log_info("命令成功")

    return result


def check_command_exists(command: str) -> bool:
    """检查命令是否存在

    Args:
        command: 命令名称（例如 "iscc", "pkgbuild"）

    Returns:
        是否存在
    """
    return shutil.which(command) is not None


# ============================================================================
# 版本比较工具
# ============================================================================

def parse_version(version_str: str) -> tuple:
    """解析版本字符串为元组

    Args:
        version_str: 版本字符串（例如 "3.1.0"）

    Returns:
        (major, minor, patch) 元组
    """
    try:
        parts = version_str.split(".")
        if len(parts) >= 3:
            return (int(parts[0]), int(parts[1]), int(parts[2]))
        return (0, 0, 0)
    except (ValueError, IndexError):
        return (0, 0, 0)


# ============================================================================
# 通知工具
# ============================================================================

def notify_send(title: str, message: str) -> bool:
    """发送桌面通知（macOS/Linux）"""
    try:
        if is_macos():
            subprocess.run(
                ["osascript", "-e",
                 f'display notification "{title}" with message "{message}"'],
                check=False,
            )
            return True
        elif is_linux():
            subprocess.run(
                ["notify-send", title, message],
                check=False,
            )
            return True
    except Exception:
        return False


# ============================================================================
# 时间工具
# ============================================================================

def format_elapsed(seconds: float) -> str:
    """格式化耗时"""
    if seconds < 60:
        return f"{seconds:.1f} 秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} 分钟"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} 小时"


class Timer:
    """计时器上下文管理器"""

    def __init__(self):
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.now()
        return self

    def __exit__(self, *args):
        if self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            log_info(f"耗时: {format_elapsed(elapsed)}")


# ============================================================================
# 主模块测试
# ============================================================================

if __name__ == "__main__":
    # 测试公共工具
    print("MediaFactory 构建公共工具模块")
    print("=" * 60)
    print(f"项目根目录: {get_project_root()}")
    print(f"项目版本: {get_project_version()}")
    print(f"平台: {get_platform_identifier()}")
    print("=" * 60)
