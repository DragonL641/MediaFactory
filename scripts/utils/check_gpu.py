"""
MediaFactory 硬件检测模块
帮助用户确定应该安装哪个版本的 PyTorch（CPU 或 CUDA）。
"""

import sys
import platform
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List, Dict


# Model info type
GPUInfo = Dict[str, Optional[str]]


def check_nvidia_gpu() -> Optional[List[GPUInfo]]:
    """检测 NVIDIA GPU

    只需要检测 GPU 是否存在，不需要复杂的 CUDA 版本查询。

    Returns:
        包含 GPU 信息的字典列表，如果没有 GPU 返回 None
    """
    # 方法1: 使用 nvidia-smi -L 检测 GPU 是否存在
    try:
        result = subprocess.run(
            ["nvidia-smi", "-L"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            # 解析 GPU 名称
            # 格式: "GPU 0: NVIDIA GeForce RTX 5070 Ti (UUID: ...)"
            gpu_info = []
            for line in result.stdout.strip().split('\n'):
                if line.startswith('GPU'):
                    # 提取 GPU 名称
                    # 格式: "GPU 0: NVIDIA GeForce RTX 5070 Ti (UUID: ...)"
                    parts = line.split(':', 1)
                    if len(parts) >= 2:
                        name_part = parts[1].strip()
                        # 去掉 UUID 部分
                        if '(' in name_part:
                            name = name_part.split('(')[0].strip()
                        else:
                            name = name_part
                        gpu_info.append({
                            'name': name,
                            'driver': None,
                            'cuda': None
                        })
            if gpu_info:
                return gpu_info
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    except Exception:
        pass

    # 方法2: 检查 nvidia-smi 命令是否存在
    if shutil.which("nvidia-smi"):
        try:
            result = subprocess.run(
                ["nvidia-smi"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                # nvidia-smi 能运行，说明有 GPU
                # 尝试从输出提取信息
                gpu_info = []
                for line in result.stdout.split('\n'):
                    if 'GPU' in line and 'Name' not in line:
                        # 尝试提取 GPU 名称
                        pass
                # 如果无法解析，返回一个默认条目
                return [{'name': 'NVIDIA GPU', 'driver': None, 'cuda': None}]
        except Exception:
            pass

    return None


def check_mps() -> bool:
    """检测 Apple Silicon GPU (MPS/MPS2 支持)

    Returns:
        是否为 Apple Silicon
    """
    try:
        result = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True,
            text=True,
        )
        return "Apple" in result.stdout
    except:
        return False


def get_recommended_cuda_version(gpu_info: Optional[List[GPUInfo]]) -> Optional[str]:
    """根据 GPU 推荐合适的 PyTorch CUDA 版本

    Args:
        gpu_info: GPU 信息列表

    Returns:
        推荐的 CUDA 版本 (cu118, cu121, cu124) 或 None
    """
    if not gpu_info:
        return None

    # 对于现代 NVIDIA GPU，直接推荐 cu124
    # CUDA 12.4 是目前最广泛支持的版本
    return "cu124"


def main():
    print("=" * 60)
    print("MediaFactory 硬件检测")
    print("=" * 60)

    # 检测 Python 版本
    print(f"\n📦 Python 版本: {sys.version.split()[0]}")

    # 检测操作系统
    os_name = platform.system()
    os_arch = platform.machine()
    print(f"\n💻 操作系统: {os_name} {os_arch}")

    # 检测 CPU
    print(f"\n🔧 CPU: {platform.processor() or 'Unknown'}")

    # 检测内存 (仅 Linux/macOS)
    if os_name in ["Linux", "Darwin"]:
        try:
            import psutil
            mem_gb = psutil.virtual_memory().total / (1024**3)
            print(f"   内存: {mem_gb:.1f} GB")
        except ImportError:
            pass

    # 检测 NVIDIA GPU
    print("\n" + "-" * 60)
    print("🎮 GPU 检测")
    print("-" * 60)

    gpu_info = check_nvidia_gpu()

    if gpu_info is not None:
        print("✅ 检测到 NVIDIA GPU:")
        for i, gpu in enumerate(gpu_info, 1):
            print(f"   GPU {i}: {gpu['name']}")

        recommended_cuda = get_recommended_cuda_version(gpu_info)
        print(f"\n   推荐安装: PyTorch {recommended_cuda} 版本")
    else:
        print("❌ 未检测到 NVIDIA GPU")
        print("   将使用 CPU 版本 PyTorch（速度较慢）")

    # 检测 Apple Silicon
    print("\n" + "-" * 60)
    print("🍎 Apple Silicon 检测")
    print("-" * 60)

    is_apple_silicon = check_mps()
    if is_apple_silicon:
        print("✅ 检测到 Apple Silicon (M1/M2/M3/M4)")
        print("   PyTorch 会自动使用 MPS 加速后端")
        print("   安装 CPU 版本即可")
    else:
        if os_name == "Darwin":
            print("❌ 未检测到 Apple Silicon (可能是 Intel Mac)")
        else:
            print("   (非 macOS 平台)")


if __name__ == "__main__":
    main()
