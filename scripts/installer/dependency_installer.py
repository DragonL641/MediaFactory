"""依赖安装模块

处理 PyTorch、transformers 等大型依赖的安装。
优先使用 uv（比 pip 快 10-100 倍），回退到 pip。
自动检测 CUDA/CPU 并安装对应的 torch 版本。
"""

import os
import sys
import shutil
import subprocess
import platform
import urllib.request
import tempfile
import stat
from typing import Optional, Tuple, List, Dict, Callable
from pathlib import Path
from dataclasses import dataclass
import time


@dataclass
class InstallProgress:
    """安装进度信息"""

    stage: str  # 当前阶段: detecting, downloading, installing, verifying, done
    progress_percent: int  # 0-100
    message: str  # 当前状态消息
    bytes_downloaded: int = 0
    total_bytes: int = 0


# Progress callback type
ProgressCallback = Callable[[InstallProgress], None]


# UV 版本和下载 URL
UV_VERSION = "0.4.30"
UV_DOWNLOAD_URLS = {
    "windows-x86_64": f"https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/uv-x86_64-pc-windows-msvc.zip",
    "linux-x86_64": f"https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/uv-x86_64-unknown-linux-gnu.tar.gz",
    "linux-aarch64": f"https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/uv-aarch64-unknown-linux-gnu.tar.gz",
    "darwin-x86_64": f"https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/uv-x86_64-apple-darwin.tar.gz",
    "darwin-aarch64": f"https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/uv-aarch64-apple-darwin.tar.gz",
}


def get_uv_download_url() -> Optional[str]:
    """获取当前平台的 uv 下载 URL"""
    system = platform.system().lower()
    machine = platform.machine().lower()

    # 标准化架构名称
    if machine in ["x86_64", "amd64"]:
        arch = "x86_64"
    elif machine in ["arm64", "aarch64"]:
        arch = "aarch64"
    else:
        return None

    key = f"{system}-{arch}"
    return UV_DOWNLOAD_URLS.get(key)


def download_uv_binary(
    output_dir: Path, progress_callback: Optional[Callable[[int, str], None]] = None
) -> Optional[Path]:
    """下载 uv 二进制文件

    Args:
        output_dir: 输出目录
        progress_callback: 进度回调 (percent, message)

    Returns:
        uv 可执行文件路径，失败返回 None
    """
    url = get_uv_download_url()
    if not url:
        return None

    output_dir.mkdir(parents=True, exist_ok=True)

    # 确定文件扩展名
    if url.endswith(".zip"):
        archive_path = output_dir / "uv.zip"
    else:
        archive_path = output_dir / "uv.tar.gz"

    try:
        if progress_callback:
            progress_callback(0, "正在下载 uv...")

        # 下载文件
        with urllib.request.urlopen(url) as response:
            total_size = int(response.headers.get("Content-Length", 0))
            block_size = 8192
            downloaded = 0

            with open(archive_path, "wb") as f:
                while True:
                    block = response.read(block_size)
                    if not block:
                        break
                    downloaded += len(block)
                    f.write(block)

                    if progress_callback and total_size > 0:
                        percent = int(downloaded / total_size * 100)
                        progress_callback(percent, f"下载 uv {percent}%")

        # 解压
        if progress_callback:
            progress_callback(100, "正在解压 uv...")

        if url.endswith(".zip"):
            import zipfile

            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                zip_ref.extractall(output_dir)
        else:
            import tarfile

            with tarfile.open(archive_path, "r:gz") as tar_ref:
                tar_ref.extractall(output_dir)

        # 查找 uv 可执行文件
        uv_bin = output_dir / "uv"
        if platform.system() == "Windows":
            uv_bin = output_dir / "uv.exe"

        # 设置可执行权限（Unix）
        if uv_bin.exists() and platform.system() != "Windows":
            st = os.stat(uv_bin)
            os.chmod(uv_bin, st.st_mode | stat.S_IEXEC)

        # 清理压缩文件
        archive_path.unlink()

        return uv_bin if uv_bin.exists() else None

    except Exception as e:
        if progress_callback:
            progress_callback(0, f"下载 uv 失败: {str(e)}")
        return None


def detect_cuda() -> Tuple[bool, Optional[str]]:
    """检测 NVIDIA GPU

    简化版：只检测 GPU 是否存在，不查询复杂的 CUDA 版本字段。
    对于 PyTorch 安装，直接使用 cu124（最新稳定版）。

    Returns:
        (has_gpu, cuda_version) 元组
        - has_gpu: 是否检测到 NVIDIA GPU
        - cuda_version: 固定返回 "12.4"（推荐安装 cu124）
    """
    # 方法1: 使用 nvidia-smi -L 检测 GPU（这个命令最稳定）
    try:
        result = subprocess.run(
            ["nvidia-smi", "-L"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            # nvidia-smi -L 能运行，说明有 GPU
            return True, "12.4"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    except Exception:
        pass

    # 方法2: 检查 nvidia-smi 命令是否存在且能运行
    try:
        result = subprocess.run(
            ["nvidia-smi"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return True, "12.4"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    except Exception:
        pass

    return False, None


def check_disk_space(required_gb: float = 10) -> Tuple[bool, float]:
    """检查磁盘空间是否足够

    Args:
        required_gb: 需要的磁盘空间（GB）

    Returns:
        (is_enough, available_gb) 元组
    """
    try:
        if platform.system() == "Windows":
            import ctypes

            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(os.getcwd()), None, None, ctypes.pointer(free_bytes)
            )
            available_gb = free_bytes.value / (1024**3)
        else:
            stat = os.statvfs(os.getcwd())
            available_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)

        return available_gb >= required_gb, available_gb
    except Exception:
        # 假设空间足够
        return True, 100.0


def get_recommended_torch_version(cuda_version: Optional[str]) -> str:
    """根据 CUDA 版本推荐 PyTorch 版本

    Args:
        cuda_version: CUDA 版本 (如 "12.1") 或 None

    Returns:
        推荐的 PyTorch 版本标识 (cu118, cu121, cu124, cpu)
    """
    if not cuda_version:
        return "cpu"

    try:
        major, minor = map(int, cuda_version.split(".")[:2])
        # CUDA 11.x → cu118
        if major == 11:
            return "cu118"
        # CUDA 12.0-12.3 → cu121
        elif major == 12 and minor < 4:
            return "cu121"
        # CUDA 12.4+ → cu124
        elif major == 12 and minor >= 4:
            return "cu124"
    except (ValueError, IndexError):
        pass

    return "cu124"  # 默认使用最新版本


class DependencyInstaller:
    """依赖安装器

    处理 PyTorch、transformers 等 ML 依赖的安装。
    优先使用 uv（比 pip 快 10-100 倍），回退到 pip。
    自动检测硬件并安装对应的版本。

    新架构：核心依赖已打包，ML 依赖为可选项
    """

    # ML 依赖（延迟安装，可在首次运行时通过安装向导安装）
    # 对应 pyproject.toml 中的 [project.optional-dependencies.ml]
    ML_DEPENDENCIES = [
        "torch>=2.0.0",
        "faster-whisper>=1.0.0",
        "transformers>=4.21.0",
        "sentencepiece>=0.1.99",
        "accelerate>=0.20.3",
        "psutil>=5.8.0",
    ]

    # Transformers 相关依赖
    TRANSFORMERS_DEPENDENCIES = [
        "transformers>=4.21.0",
        "accelerate>=0.20.3",
        "sentencepiece>=0.1.99",
    ]

    def __init__(self, python_path: Optional[str] = None):
        """初始化安装器

        Args:
            python_path: Python 解释器路径，默认使用当前 Python
        """
        self.python_path = python_path or sys.executable
        self.platform = platform.system()
        self.arch = platform.machine()
        self._uv_path: Optional[Path] = None
        self._use_uv = True  # 默认尝试使用 uv

    def _get_uv_path(self) -> Optional[Path]:
        """获取 uv 可执行文件路径

        Returns:
            uv 路径，如果不可用返回 None
        """
        if self._uv_path is not None:
            return self._uv_path if self._uv_path.exists() else None

        # 1. 检查系统 PATH 中的 uv
        uv_in_path = shutil.which("uv")
        if uv_in_path:
            self._uv_path = Path(uv_in_path)
            return self._uv_path

        # 2. 检查项目根目录中的 uv
        project_root = Path(__file__).parent.parent.parent.resolve()
        local_uv = (
            project_root / "uv.exe"
            if self.platform == "Windows"
            else project_root / "uv"
        )
        if local_uv.exists():
            self._uv_path = local_uv
            return self._uv_path

        return None

    def _ensure_uv(self, progress_callback: Optional[ProgressCallback] = None) -> bool:
        """确保 uv 可用，尝试下载

        Args:
            progress_callback: 进度回调

        Returns:
            是否可用
        """
        if not self._use_uv:
            return False

        uv_path = self._get_uv_path()
        if uv_path:
            return True

        # 尝试下载 uv
        if progress_callback:
            progress_callback(
                InstallProgress(
                    stage="downloading",
                    progress_percent=0,
                    message="uv 未找到，正在下载（比 pip 快 10-100 倍）...",
                )
            )

        project_root = Path(__file__).parent.parent.parent.resolve()

        def uv_progress(percent: int, msg: str):
            if progress_callback:
                progress_callback(
                    InstallProgress(
                        stage="downloading", progress_percent=percent, message=msg
                    )
                )

        uv_bin = download_uv_binary(project_root, uv_progress)
        if uv_bin:
            self._uv_path = uv_bin
            if progress_callback:
                progress_callback(
                    InstallProgress(
                        stage="done", progress_percent=100, message="uv 下载完成"
                    )
                )
            return True

        # 下载失败，禁用 uv
        self._use_uv = False
        if progress_callback:
            progress_callback(
                InstallProgress(
                    stage="downloading",
                    progress_percent=0,
                    message="uv 下载失败，将使用 pip",
                )
            )
        return False

    def _run_pip(
        self, args: List[str], capture_output: bool = True
    ) -> subprocess.CompletedProcess:
        """运行 pip 命令

        Args:
            args: pip 参数列表
            capture_output: 是否捕获输出

        Returns:
            subprocess.CompletedProcess
        """
        cmd = [self.python_path, "-m", "pip"] + args
        return subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
        )

    def _run_uv(
        self, args: List[str], capture_output: bool = True
    ) -> subprocess.CompletedProcess:
        """运行 uv 命令

        Args:
            args: uv 参数列表
            capture_output: 是否捕获输出

        Returns:
            subprocess.CompletedProcess
        """
        uv_path = self._get_uv_path()
        if not uv_path:
            raise RuntimeError("uv 不可用")

        cmd = [str(uv_path)] + args
        return subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
        )

    def _ensure_pip(self) -> bool:
        """确保 pip 可用

        Returns:
            是否成功
        """
        try:
            result = subprocess.run(
                [self.python_path, "-m", "pip", "--version"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode != 0:
                # 尝试安装 pip
                subprocess.run(
                    [self.python_path, "-m", "ensurepip", "--upgrade"],
                    capture_output=True,
                    timeout=60,
                )
            return True
        except Exception:
            return False

    def _install_with_progress(
        self,
        packages: List[str],
        progress_callback: Optional[ProgressCallback] = None,
        extra_index_url: Optional[str] = None,
    ) -> bool:
        """安装包并报告进度（优先使用 uv）

        Args:
            packages: 要安装的包列表
            progress_callback: 进度回调函数
            extra_index_url: 额外的索引 URL（用于 CUDA 版本的 PyTorch）

        Returns:
            是否成功
        """
        if progress_callback:
            progress_callback(
                InstallProgress(
                    stage="preparing",
                    progress_percent=0,
                    message=f"正在准备下载 {len(packages)} 个包...",
                )
            )

        # 尝试使用 uv
        use_uv = self._ensure_uv(progress_callback)
        installer = "uv" if use_uv else "pip"

        if progress_callback:
            speed_hint = "（使用 uv，超快！）" if use_uv else "（使用 pip）"
            progress_callback(
                InstallProgress(
                    stage="downloading",
                    progress_percent=5,
                    message=f"正在使用 {installer} 下载依赖{speed_hint}",
                )
            )

        if use_uv:
            return self._install_with_uv(packages, progress_callback, extra_index_url)
        else:
            return self._install_with_pip(packages, progress_callback, extra_index_url)

    def _install_with_uv(
        self,
        packages: List[str],
        progress_callback: Optional[ProgressCallback] = None,
        extra_index_url: Optional[str] = None,
    ) -> bool:
        """使用 uv 安装包

        Args:
            packages: 要安装的包列表
            progress_callback: 进度回调函数
            extra_index_url: 额外的索引 URL

        Returns:
            是否成功
        """
        # uv pip install 命令
        args = ["pip", "install", "--upgrade"]
        if extra_index_url:
            args.extend(["--extra-index-url", extra_index_url])
        args.extend(packages)

        # 执行安装
        process = subprocess.Popen(
            [str(self._get_uv_path())] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # 解析进度
        last_progress = 10
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue

            # uv 的进度输出
            if progress_callback:
                # 简单的进度估算
                if "Resolved" in line or "Installed" in line or "Downloading" in line:
                    last_progress = min(last_progress + 10, 90)
                    progress_callback(
                        InstallProgress(
                            stage="installing",
                            progress_percent=last_progress,
                            message=line[:100],  # 限制长度
                        )
                    )

        returncode = process.wait()

        if returncode == 0 and progress_callback:
            progress_callback(
                InstallProgress(
                    stage="installing", progress_percent=100, message="安装完成"
                )
            )

        return returncode == 0

    def _install_with_pip(
        self,
        packages: List[str],
        progress_callback: Optional[ProgressCallback] = None,
        extra_index_url: Optional[str] = None,
    ) -> bool:
        """使用 pip 安装包

        Args:
            packages: 要安装的包列表
            progress_callback: 进度回调函数
            extra_index_url: 额外的索引 URL

        Returns:
            是否成功
        """
        args = ["install", "--upgrade"]
        if extra_index_url:
            args.extend(["--extra-index-url", extra_index_url])
        args.extend(packages)

        # 执行安装
        process = subprocess.Popen(
            [self.python_path, "-m", "pip"] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # 解析进度
        last_progress = 10
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue

            # 简单的进度估算
            if "Downloading" in line or "Installing" in line:
                if progress_callback:
                    # 逐步增加进度
                    last_progress = min(last_progress + 5, 90)
                    progress_callback(
                        InstallProgress(
                            stage=(
                                "downloading" if "Downloading" in line else "installing"
                            ),
                            progress_percent=last_progress,
                            message=line[:100],  # 限制长度
                        )
                    )

        returncode = process.wait()

        if returncode == 0 and progress_callback:
            progress_callback(
                InstallProgress(
                    stage="installing", progress_percent=100, message="安装完成"
                )
            )

        return returncode == 0

    def verify_installation(self, package: str) -> bool:
        """验证包是否已安装

        Args:
            package: 包名

        Returns:
            是否已安装
        """
        try:
            result = self._run_pip(["show", package])
            return result.returncode == 0
        except Exception:
            return False

    def install_ml_dependencies(
        self,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> bool:
        """安装 ML 依赖（本地 ASR 和翻译功能）

        Args:
            progress_callback: 进度回调函数

        Returns:
            是否成功
        """
        if progress_callback:
            progress_callback(
                InstallProgress(
                    stage="installing",
                    progress_percent=0,
                    message="正在安装 ML 依赖...",
                )
            )

        success = self._install_with_progress(
            self.ML_DEPENDENCIES,
            progress_callback,
        )

        if success and progress_callback:
            progress_callback(
                InstallProgress(
                    stage="installing", progress_percent=100, message="ML 依赖安装完成"
                )
            )

        return success

    def install_torch(
        self,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> bool:
        """安装 PyTorch（自动检测 CUDA/CPU）

        Args:
            progress_callback: 进度回调函数

        Returns:
            是否成功
        """
        if progress_callback:
            progress_callback(
                InstallProgress(
                    stage="detecting", progress_percent=0, message="正在检测 GPU..."
                )
            )

        # 检测 CUDA
        has_cuda, cuda_version = detect_cuda()
        torch_version = get_recommended_torch_version(cuda_version)

        if progress_callback:
            if has_cuda:
                progress_callback(
                    InstallProgress(
                        stage="detecting",
                        progress_percent=10,
                        message=f"检测到 NVIDIA GPU (CUDA {cuda_version})",
                    )
                )
            else:
                progress_callback(
                    InstallProgress(
                        stage="detecting",
                        progress_percent=10,
                        message="未检测到 NVIDIA GPU，将安装 CPU 版本",
                    )
                )

        # 确定安装 URL
        if torch_version == "cpu":
            index_url = "https://download.pytorch.org/whl/cpu"
            package = "torch"
        else:
            index_url = f"https://download.pytorch.org/whl/{torch_version}"
            package = "torch"

        if progress_callback:
            progress_callback(
                InstallProgress(
                    stage="downloading",
                    progress_percent=20,
                    message=f"正在从 PyTorch 官方源下载 {torch_version} 版本...",
                )
            )

        # 安装 PyTorch
        success = self._install_with_progress(
            [package],
            progress_callback,
            extra_index_url=index_url,
        )

        # 验证安装
        if success:
            try:
                import torch

                if progress_callback:
                    device = "CUDA" if torch.cuda.is_available() else "CPU"
                    progress_callback(
                        InstallProgress(
                            stage="verifying",
                            progress_percent=100,
                            message=f"PyTorch {torch.__version__} ({device}) 安装成功",
                        )
                    )
            except ImportError:
                success = False

        return success

    def install_transformers(
        self,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> bool:
        """安装 transformers 及相关依赖

        Args:
            progress_callback: 进度回调函数

        Returns:
            是否成功
        """
        if progress_callback:
            progress_callback(
                InstallProgress(
                    stage="installing",
                    progress_percent=0,
                    message="正在安装 transformers 和相关依赖...",
                )
            )

        packages = [
            "transformers>=4.30.0",
            "accelerate>=0.20.0",
            "sentencepiece>=0.1.99",
        ]

        success = self._install_with_progress(packages, progress_callback)

        if success and progress_callback:
            progress_callback(
                InstallProgress(
                    stage="installing",
                    progress_percent=100,
                    message="transformers 安装完成",
                )
            )

        return success

    def install_all(
        self,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> bool:
        """安装所有 ML 依赖

        注意：核心依赖已在 PyInstaller 打包中包含，此方法仅安装 ML 依赖。

        Args:
            progress_callback: 进度回调函数

        Returns:
            是否成功
        """
        # 1. 检查磁盘空间
        if progress_callback:
            progress_callback(
                InstallProgress(
                    stage="detecting", progress_percent=0, message="正在检查磁盘空间..."
                )
            )

        has_space, space_gb = check_disk_space(required_gb=5)
        if not has_space:
            if progress_callback:
                progress_callback(
                    InstallProgress(
                        stage="detecting",
                        progress_percent=0,
                        message=f"磁盘空间不足: 需要 5GB，可用 {space_gb:.1f}GB",
                    )
                )
            return False

        # 2. 确保 uv 或 pip 可用
        if not self._ensure_uv(progress_callback):
            if not self._ensure_pip():
                return False

        # 3. 安装 ML 依赖（包含 PyTorch、transformers、faster-whisper 等）
        if not self.install_ml_dependencies(progress_callback):
            return False

        if progress_callback:
            progress_callback(
                InstallProgress(
                    stage="done", progress_percent=100, message="ML 依赖安装完成！"
                )
            )

        return True


# 导出
__all__ = [
    "DependencyInstaller",
    "detect_cuda",
    "check_disk_space",
    "get_recommended_torch_version",
    "InstallProgress",
    "ProgressCallback",
    "get_uv_download_url",
    "download_uv_binary",
]
