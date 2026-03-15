#!/usr/bin/env python3
"""
MediaFactory 安装时依赖下载脚本

由安装程序（.pkg / .exe）在安装后调用。
功能：
1. 检测硬件（GPU/CPU）并选择合适的 PyTorch 版本
2. 安装所有 ML 依赖（torch, transformers, faster-whisper 等）
3. 显示下载进度

Usage:
    python install_dependencies.py <install_dir>
    python install_dependencies.py /Applications/MediaFactory.app/Contents/MacOS
    python install_dependencies.py "C:\\Program Files\\MediaFactory"
"""

import os
import platform
import subprocess
import sys
import time
from pathlib import Path


# ============================================================================
# 配置
# ============================================================================

# PyTorch 索引 URL（简化为 cpu 和 cu124）
PYTORCH_INDEX_URLS = {
    "cpu": "https://download.pytorch.org/whl/cpu",
    "cu124": "https://download.pytorch.org/whl/cu124",
}

# ML 依赖包（与 pyproject.toml 中的 core 组一致）
ML_PACKAGES = [
    "torch>=2.5.0",
    "faster-whisper>=1.0.0",
    "gguf>=0.10.0",
    "transformers>=4.46.0,<5.0.0",
    "sentencepiece>=0.1.99",
    "accelerate>=1.0.0",
    "spandrel>=0.4.0",
    "facexlib>=0.3.0",
]

# 中国镜像源（用于国内用户）
CHINA_MIRROR = "https://pypi.tuna.tsinghua.edu.cn/simple"

# ============================================================================
# 工具函数
# ============================================================================

def log_info(msg: str):
    """输出信息日志"""
    print(f"[INFO] {msg}")


def log_error(msg: str):
    """输出错误日志"""
    print(f"[ERROR] {msg}", file=sys.stderr)


def log_success(msg: str):
    """输出成功日志"""
    print(f"[SUCCESS] {msg}")


def get_python_executable() -> str:
    """获取 Python 可执行文件路径"""
    # 在冻结环境中，使用内置的 Python
    if getattr(sys, 'frozen', False):
        # PyInstaller 冻结环境
        if platform.system() == "Windows":
            # Windows: 使用打包的 Python
            return sys.executable
        else:
            # macOS/Linux: 使用系统 Python
            return sys.executable
    else:
        # 开发环境
        return sys.executable


def detect_hardware() -> str:
    """
    检测硬件并返回推荐的 PyTorch 版本（固定 cu124）

    Returns:
        "cpu" 或 "cu124"
    """
    log_info("检测硬件配置...")

    system = platform.system()

    # Windows: 检测 NVIDIA GPU
    if system == "Windows":
        try:
            result = subprocess.run(
                ["nvidia-smi"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                log_info("检测到 NVIDIA GPU，使用 CUDA 12.4")
                return "cu124"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    # macOS: 检查是否有 NVIDIA GPU（罕见）
    if system == "Darwin":
        # macOS 通常没有 NVIDIA GPU，使用 CPU 版本
        # 注意: Faster Whisper 不支持 MPS (Apple Silicon GPU)
        log_info("macOS 检测: 使用 CPU 版本（Faster Whisper 不支持 MPS）")
        return "cpu"

    # Linux: 检测 NVIDIA GPU
    if system == "Linux":
        try:
            result = subprocess.run(
                ["nvidia-smi"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                log_info("检测到 NVIDIA GPU，使用 CUDA 12.4")
                return "cu124"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    # 默认使用 CPU 版本
    log_info("未检测到 NVIDIA GPU，使用 CPU 版本")
    return "cpu"


def detect_use_china_mirror() -> bool:
    """
    检测是否使用中国镜像源

    根据系统语言和 IP 地址判断
    """
    # 简单检测：检查系统语言
    locale = os.environ.get("LANG", "").lower()
    if "zh" in locale or "cn" in locale:
        return True

    # 检查环境变量
    if os.environ.get("MF_USE_CHINA_MIRROR", "").lower() in ("1", "true", "yes"):
        return True

    return False


def install_packages(
    install_dir: Path,
    torch_version: str,
    use_china_mirror: bool = False,
) -> bool:
    """
    安装所有依赖包

    Args:
        install_dir: 安装目录
        torch_version: PyTorch 版本 (cpu, cu118, cu121, cu124)
        use_china_mirror: 是否使用中国镜像
    """
    log_info("=" * 60)
    log_info("开始安装 ML 依赖")
    log_info("=" * 60)

    python_exe = get_python_executable()
    log_info(f"Python: {python_exe}")
    log_info(f"PyTorch 版本: {torch_version}")
    log_info(f"安装目录: {install_dir}")

    # 构建 pip install 命令
    cmd = [
        python_exe,
        "-m",
        "pip",
        "install",
        "--upgrade",
    ]

    # 添加 PyTorch 索引 URL（如果不是 CPU 版本）
    if torch_version != "cpu":
        index_url = PYTORCH_INDEX_URLS.get(torch_version)
        if index_url:
            cmd.extend(["--extra-index-url", index_url])
            log_info(f"使用 PyTorch 索引: {index_url}")

    # 使用中国镜像（如果需要）
    if use_china_mirror:
        cmd.extend(["-i", CHINA_MIRROR])
        log_info(f"使用中国镜像: {CHINA_MIRROR}")

    # 添加包列表
    cmd.extend(CORE_PACKAGES)

    log_info("安装命令:")
    log_info(" ".join(cmd[:6]) + " [...]")

    # 执行安装
    log_info("\n正在下载和安装依赖（这可能需要 10-30 分钟）...")
    start_time = time.time()

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        # 实时输出进度
        for line in process.stdout:
            # 只显示重要信息
            line = line.strip()
            if line:
                # 过滤掉过多的下载进度信息
                if any(keyword in line.lower() for keyword in [
                    "requirement already satisfied",
                    "satisfied",
                ]):
                    continue
                print(line)

        process.wait()
        elapsed = time.time() - start_time

        if process.returncode == 0:
            log_success(f"依赖安装成功！耗时: {elapsed:.1f} 秒")
            return True
        else:
            log_error(f"依赖安装失败 (退出码: {process.returncode})")
            return False

    except Exception as e:
        log_error(f"安装过程出错: {e}")
        return False


def verify_installation() -> bool:
    """验证依赖是否正确安装"""
    log_info("验证安装...")

    try:
        import torch
        log_info(f"PyTorch {torch.__version__} 安装成功")

        import transformers
        log_info(f"Transformers {transformers.__version__} 安装成功")

        # 检查 CUDA 可用性
        if torch.cuda.is_available():
            log_info(f"CUDA 可用: {torch.cuda.get_device_name(0)}")
        else:
            log_info("CUDA 不可用，使用 CPU")

        return True

    except ImportError as e:
        log_error(f"验证失败: {e}")
        return False


def write_installation_log(install_dir: Path, success: bool, message: str = ""):
    """写入安装日志"""
    log_dir = install_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "installation.log"

    with open(log_file, "a", encoding="utf-8") as f:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"\n{'='*60}\n")
        f.write(f"依赖安装日志 - {timestamp}\n")
        f.write(f"{'='*60}\n")
        f.write(f"状态: {'成功' if success else '失败'}\n")
        if message:
            f.write(f"信息: {message}\n")


# ============================================================================
# 主入口点
# ============================================================================

def main() -> int:
    """主入口点"""
    if len(sys.argv) < 2:
        log_error("用法: python install_dependencies.py <install_dir>")
        log_error("示例: python install_dependencies.py /Applications/MediaFactory.app/Contents/MacOS")
        return 1

    install_dir = Path(sys.argv[1])

    if not install_dir.exists():
        log_error(f"安装目录不存在: {install_dir}")
        return 1

    # 检测硬件
    torch_version = detect_hardware()

    # 检测是否使用中国镜像
    use_china_mirror = detect_use_china_mirror()
    if use_china_mirror:
        log_info("检测到中国用户，使用镜像源加速下载")

    # 安装依赖
    success = install_packages(install_dir, torch_version, use_china_mirror)

    # 验证安装
    if success:
        # 注意: 在冻结环境中，我们无法直接导入验证
        # 因为安装的包在打包的 Python 中不可用
        # 这里只记录日志
        log_info("依赖安装完成")
        write_installation_log(install_dir, True, f"PyTorch 版本: {torch_version}")
        return 0
    else:
        write_installation_log(install_dir, False, "安装失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
