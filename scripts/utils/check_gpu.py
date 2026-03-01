"""
MediaFactory 硬件检测模块
帮助用户确定应该安装哪个版本的 PyTorch（CPU 或 CUDA）。
"""

import sys
import platform
import subprocess
from pathlib import Path
from typing import Optional, List, Dict


# Model info type
GPUInfo = Dict[str, Optional[str]]


def check_nvidia_gpu() -> Optional[List[GPUInfo]]:
    """检测 NVIDIA GPU 及 CUDA 版本

    Returns:
        包含 GPU 信息的字典列表，如果没有 GPU 返回 None
    """
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version,cuda_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            gpu_info = []
            for line in lines:
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 3:
                    gpu_info.append({
                        'name': parts[0],
                        'driver': parts[1],
                        'cuda': parts[2] if parts[2] != 'N/A' else None
                    })
            return gpu_info if gpu_info else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
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
    """根据 GPU 的 CUDA 版本推荐合适的 PyTorch CUDA 版本

    Args:
        gpu_info: GPU 信息列表

    Returns:
        推荐的 CUDA 版本 (cu118, cu121, cu124)
    """
    if not gpu_info:
        return None

    # 获取第一个 GPU 的 CUDA 版本
    cuda_version = gpu_info[0].get('cuda')
    if not cuda_version:
        return "cu124"  # 默认使用最新的

    try:
        major, minor = map(int, cuda_version.split('.'))

        # CUDA 11.x → cu118
        if major == 11:
            return "cu118"
        # CUDA 12.0-12.3 → cu121
        elif major == 12 and minor < 4:
            return "cu121"
        # CUDA 12.4+ → cu124
        elif major == 12 and minor >= 4:
            return "cu124"
        # 未知版本 → 使用最新的
        else:
            return "cu124"
    except:
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
            print(f"   GPU {i}:")
            print(f"      名称: {gpu['name']}")
            print(f"      驱动: {gpu['driver']}")
            if gpu['cuda']:
                print(f"      CUDA: {gpu['cuda']}")

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
