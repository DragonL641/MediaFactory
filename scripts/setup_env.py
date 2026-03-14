#!/usr/bin/env python3
"""
MediaFactory 环境初始化向导

交互式脚本，用于：
1. 检测用户环境和硬件
2. 根据用户身份（开发者/使用者）安装依赖
3. 可选预下载 AI 模型

Usage:
    python scripts/setup_env.py
"""

import os
import sys
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

# 复用现有模块
try:
    from utils.check_gpu import (
        check_nvidia_gpu,
        get_recommended_cuda_version,
        check_mps,
    )
    from installer.dependency_installer import (
        detect_cuda,
        check_disk_space,
        get_recommended_torch_version,
    )
    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False


# ANSI 颜色代码
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    # 菜单高亮
    REVERSE = '\033[7m'

    # Windows 兼容
    if platform.system() == "Windows":
        os.system('color')


def clear_screen():
    """清屏"""
    os.system('cls' if platform.system() == "Windows" else 'clear')


def print_color(text: str, color: str = Colors.ENDC) -> None:
    """打印带颜色的文本"""
    print(f"{color}{text}{Colors.ENDC}")


def print_header(text: str) -> None:
    """打印标题"""
    width = 62
    print()
    print_color("╔" + "═" * (width - 2) + "╗", Colors.CYAN)
    print_color("║" + text.center(width - 2) + "║", Colors.CYAN)
    print_color("╚" + "═" * (width - 2) + "╝", Colors.CYAN)
    print()


def print_section(title: str) -> None:
    """打印分节标题"""
    print()
    print_color(f"{'─' * 20} {title} {'─' * 20}", Colors.BLUE)


def print_success(text: str) -> None:
    """打印成功信息"""
    print_color(f"  ✓ {text}", Colors.GREEN)


def print_error(text: str) -> None:
    """打印错误信息"""
    print_color(f"  ✗ {text}", Colors.RED)


def print_info(text: str) -> None:
    """打印信息"""
    print_color(f"  • {text}", Colors.DIM)


def print_warning(text: str) -> None:
    """打印警告"""
    print_color(f"  ⚠ {text}", Colors.YELLOW)


def select_menu(title: str, options: List[Tuple[str, str]], default: int = 0) -> int:
    """交互式菜单选择

    Args:
        title: 菜单标题
        options: 选项列表 [(显示文本, 描述), ...]
        default: 默认选项索引

    Returns:
        选择的选项索引
    """
    # 在 Windows 上使用 msvcrt 实现方向键选择
    if platform.system() == "Windows":
        return _windows_menu(title, options, default)
    else:
        # 在其他平台上尝试 curses
        try:
            return _curses_menu(title, options, default)
        except Exception:
            return _simple_menu(title, options, default)


def _windows_menu(title: str, options: List[Tuple[str, str]], default: int = 0) -> int:
    """使用 msvcrt 实现的 Windows 交互式菜单"""
    import msvcrt

    current = default

    def render():
        os.system('cls' if platform.system() == "Windows" else 'clear')
        print_header("MediaFactory 环境初始化向导")

        print()
        print_color(f"  {title}", Colors.BOLD)
        print()
        print_color("  使用 ↑/↓ 选择，Enter 确认", Colors.DIM)
        print()

        for idx, (label, desc) in enumerate(options):
            if idx == current:
                print_color(f"  → [{idx + 1}] {label}", Colors.REVERSE)
                print_color(f"      {desc}", Colors.DIM)
            else:
                print(f"    [{idx + 1}] {label}")
                print_color(f"      {desc}", Colors.DIM)

        print()

    render()

    while True:
        key = msvcrt.getch()

        if key == b'\xe0':  # 方向键前缀
            key = msvcrt.getch()
            if key == b'H' and current > 0:  # 上
                current -= 1
                render()
            elif key == b'P' and current < len(options) - 1:  # 下
                current += 1
                render()
        elif key == b'\r':  # Enter
            return current
        elif key == b'\x1b':  # Esc
            return default
        elif key in (b'1', b'2', b'3', b'4'):  # 数字快捷键
            idx = int(key) - 1
            if 0 <= idx < len(options):
                return idx


def _curses_menu(title: str, options: List[Tuple[str, str]], default: int = 0) -> int:
    """使用 curses 实现的交互式菜单"""
    import curses

    def menu(stdscr):
        curses.curs_set(0)  # 隐藏光标
        stdscr.clear()

        current_row = default
        height, width = stdscr.getmaxyx()

        while True:
            stdscr.clear()

            # 显示标题
            stdscr.addstr(2, (width - len(title)) // 2, title, curses.A_BOLD)
            stdscr.addstr(4, 2, "使用 ↑/↓ 选择，Enter 确认，Esc 使用默认值")
            stdscr.addstr(5, 2, "─" * (width - 4))

            # 显示选项
            for idx, (label, desc) in enumerate(options):
                y = 7 + idx * 2
                x = 4

                if idx == current_row:
                    stdscr.addstr(y, x, f"→ {label}", curses.A_REVERSE)
                    stdscr.addstr(y + 1, x + 2, f"  {desc}", curses.A_DIM)
                else:
                    stdscr.addstr(y, x, f"  {label}")
                    stdscr.addstr(y + 1, x + 2, f"  {desc}", curses.A_DIM)

            stdscr.refresh()

            key = stdscr.getch()

            if key == curses.KEY_UP and current_row > 0:
                current_row -= 1
            elif key == curses.KEY_DOWN and current_row < len(options) - 1:
                current_row += 1
            elif key == curses.KEY_ENTER or key in (10, 13):  # Enter
                return current_row
            elif key == 27:  # Esc
                return default
            elif key in (ord('1'), ord('2'), ord('3'), ord('4')):
                # 数字快捷键
                num = key - ord('1')
                if 0 <= num < len(options):
                    return num

        return default

    return curses.wrapper(menu)


def _simple_menu(title: str, options: List[Tuple[str, str]], default: int = 0) -> int:
    """简单输入菜单（回退方案）"""
    print()
    print_color(f"  {title}", Colors.BOLD)
    print()

    for idx, (label, desc) in enumerate(options):
        marker = "→" if idx == default else " "
        print(f"  {marker} [{idx + 1}] {label}")
        print_color(f"      {desc}", Colors.DIM)

    print()

    while True:
        prompt = f"  请选择 (1-{len(options)}) [默认: {default + 1}]: "
        choice = input(prompt).strip()

        if not choice:
            return default

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return idx
        except ValueError:
            pass

        print_warning(f"请输入 1-{len(options)}")


class SetupWizard:
    """环境初始化向导"""

    # 预定义的模型列表（用于预下载）
    PRESET_MODELS = [
        "Systran/faster-whisper-large-v3",
        "google/madlad400-3b-mt",
    ]

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.is_developer = False
        self.use_china_mirror = False
        self.env_status: Dict[str, any] = {}
        self.gpu_info: Optional[List[Dict]] = None
        self.cuda_version: Optional[str] = None
        self.torch_version: Optional[str] = None

    def run(self) -> bool:
        """运行向导"""
        try:
            self.show_welcome()
            self.detect_and_show_environment()

            # 检查是否已完成设置
            if self.check_already_setup():
                print_section("环境已配置")
                print_info("检测到环境已完成配置")

                options = [
                    ("跳过配置", "使用现有环境"),
                    ("重新配置", "重新安装所有依赖"),
                ]
                choice = select_menu("是否重新配置？", options, default=0)

                if choice == 0:
                    print_success("跳过配置，使用现有环境")
                    self.show_completion(skip_setup=True)
                    return True

            # 用户角色选择
            role_options = [
                ("使用者", "仅安装运行时依赖（推荐）"),
                ("开发者", "安装运行时 + 开发依赖"),
            ]
            role_idx = select_menu("请选择您的身份", role_options, default=0)
            self.is_developer = (role_idx == 1)
            role = "开发者" if self.is_developer else "使用者"
            print_success(f"已选择: {role}")

            # 镜像源选择
            mirror_options = [
                ("官方源", "推荐，速度稳定"),
                ("国内镜像", "适合中国大陆用户（清华源）"),
            ]
            mirror_idx = select_menu("选择下载源", mirror_options, default=0)
            self.use_china_mirror = (mirror_idx == 1)
            source = "国内镜像 (pypi.tuna.tsinghua.edu.cn)" if self.use_china_mirror else "官方源"
            print_success(f"已选择: {source}")

            # 执行安装
            self.install_dependencies()

            # 模型下载选择
            model_options = [
                ("下载模型", "推荐，稍后可立即使用（约 15GB）"),
                ("跳过下载", "稍后在应用内下载"),
            ]
            model_idx = select_menu("是否预下载 AI 模型？", model_options, default=0)

            if model_idx == 0:
                self._download_models()
            else:
                print_info("跳过模型下载，您可以稍后在应用内下载")

            self.show_completion()
            return True

        except KeyboardInterrupt:
            print("\n\n")
            print_warning("设置已取消")
            return False
        except Exception as e:
            print_error(f"设置过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
            return False

    def show_welcome(self) -> None:
        """显示欢迎信息"""
        print_header("MediaFactory 环境初始化向导")
        print_info("此脚本将帮助您配置 MediaFactory 开发/运行环境")
        print()
        print_info("将执行以下步骤：")
        print("    1. 检测您的系统环境")
        print("    2. 安装 Python 依赖")
        print("    3. 配置 PyTorch (CPU/GPU)")
        print("    4. 可选：下载 AI 模型")

    def detect_and_show_environment(self) -> None:
        """检测并展示环境信息"""
        print_section("环境检测")

        # 检测 Python 版本
        python_version = sys.version.split()[0]
        print_info(f"Python: {python_version}")

        # 检测操作系统
        os_name = platform.system()
        os_arch = platform.machine()
        print_info(f"操作系统: {os_name} ({os_arch})")

        # 检测 GPU（复用 check_gpu.py）
        if MODULES_AVAILABLE:
            self.gpu_info = check_nvidia_gpu()
            if self.gpu_info:
                for gpu in self.gpu_info:
                    print_info(f"GPU: {gpu['name']}")
            else:
                print_info("GPU: 未检测到 NVIDIA GPU")

            # 检测 Apple Silicon
            if check_mps():
                print_info("检测到 Apple Silicon (MPS 加速可用)")
        else:
            print_warning("硬件检测模块不可用，跳过 GPU 检测")

        # 检测磁盘空间
        has_space, space_gb = self._check_disk_space()
        print_info(f"磁盘空间: {space_gb:.1f} GB 可用")
        if not has_space:
            print_warning("建议至少保留 10GB 空间")

        # 检测已安装组件
        self.env_status = self._check_existing_environment()
        print()
        print_info("已安装组件：")
        print(f"    • uv: {'✅' if self.env_status['uv'] else '❌'}")
        print(f"    • PyTorch: {'✅' if self.env_status['pytorch'] else '❌'}")
        if self.env_status['pytorch'] and self.env_status.get('pytorch_cuda'):
            print(f"        CUDA: {self.env_status['pytorch_cuda']}")
        print(f"    • 项目依赖: {'✅' if self.env_status['dependencies'] else '❌'}")

    def _check_disk_space(self, required_gb: float = 10) -> Tuple[bool, float]:
        """检查磁盘空间"""
        if MODULES_AVAILABLE:
            return check_disk_space(required_gb)
        else:
            # 简单回退实现
            try:
                if platform.system() == "Windows":
                    import ctypes
                    free_bytes = ctypes.c_ulonglong(0)
                    ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                        ctypes.c_wchar_p(str(self.project_root)), None, None,
                        ctypes.pointer(free_bytes)
                    )
                    available_gb = free_bytes.value / (1024**3)
                else:
                    stat = os.statvfs(self.project_root)
                    available_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
                return available_gb >= required_gb, available_gb
            except Exception:
                return True, 100.0

    def _check_existing_environment(self) -> Dict[str, any]:
        """检查已安装的组件"""
        status = {
            'uv': self._check_uv_installed(),
            'pytorch': self._check_pytorch_installed(),
            'pytorch_cuda': None,
            'dependencies': self._check_dependencies_installed(),
        }

        if status['pytorch']:
            status['pytorch_cuda'] = self._check_pytorch_cuda_support()

        return status

    def _check_uv_installed(self) -> bool:
        """检查 uv 是否已安装"""
        if shutil.which("uv"):
            return True
        local_uv = self.project_root / ("uv.exe" if platform.system() == "Windows" else "uv")
        return local_uv.exists()

    def _check_pytorch_installed(self) -> bool:
        """检查 PyTorch 是否已安装"""
        try:
            result = subprocess.run(
                [sys.executable, "-c", "import torch; print(torch.__version__)"],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    def _check_pytorch_cuda_support(self) -> Optional[str]:
        """检查 PyTorch 的 CUDA 支持版本"""
        try:
            result = subprocess.run(
                [sys.executable, "-c",
                 "import torch; print(torch.version.cuda if torch.cuda.is_available() else 'cpu')"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                cuda = result.stdout.strip()
                return cuda if cuda and cuda != 'None' else 'cpu'
        except Exception:
            pass
        return None

    def _check_dependencies_installed(self) -> bool:
        """检查项目依赖是否已安装"""
        try:
            result = subprocess.run(
                [sys.executable, "-c", "import mediafactory; print('ok')"],
                capture_output=True, text=True, timeout=10,
                cwd=str(self.project_root)
            )
            return result.returncode == 0 and 'ok' in result.stdout
        except Exception:
            return False

    def check_already_setup(self) -> bool:
        """检查是否已完成设置"""
        return (
            self.env_status.get('uv', False) and
            self.env_status.get('pytorch', False) and
            self.env_status.get('dependencies', False)
        )

    def install_dependencies(self) -> None:
        """安装依赖"""
        print_section("安装依赖")

        steps = []

        # 1. 确保 uv 可用
        if not self._check_uv_installed():
            steps.append(("安装 uv", self._ensure_uv))
        else:
            print_success("uv 已就绪")

        # 2. 安装 PyTorch
        if not self.env_status.get('pytorch'):
            steps.append(("安装 PyTorch", self._install_pytorch))
        else:
            print_success("PyTorch 已安装")
            if self.env_status.get('pytorch_cuda'):
                self.torch_version = f"CUDA {self.env_status['pytorch_cuda']}"

        # 3. 安装项目依赖
        if not self.env_status.get('dependencies'):
            steps.append(("安装项目依赖", self._install_project_dependencies))
        else:
            print_success("项目依赖已安装")

        # 执行需要安装的步骤
        for step_name, step_func in steps:
            print_info(f"正在{step_name}...")
            if step_func():
                print_success(f"{step_name}完成")
            else:
                print_warning(f"{step_name}可能存在问题")

        print_success("依赖安装流程完成")

    def _ensure_uv(self) -> bool:
        """确保 uv 可用"""
        if self._check_uv_installed():
            return True

        pip_args = [sys.executable, "-m", "pip", "install", "uv", "-q"]

        if self.use_china_mirror:
            pip_args.extend(["-i", "https://pypi.tuna.tsinghua.edu.cn/simple"])

        try:
            result = subprocess.run(
                pip_args,
                capture_output=True, text=True, timeout=120
            )
            return result.returncode == 0
        except Exception:
            return False

    def _install_pytorch(self) -> bool:
        """安装 PyTorch"""
        # 确定 CUDA 版本
        if MODULES_AVAILABLE:
            has_cuda, cuda_ver = detect_cuda()
            torch_ver = get_recommended_torch_version(cuda_ver)
        else:
            if self.gpu_info:
                torch_ver = "cu124"
            else:
                torch_ver = "cpu"

        if torch_ver == "cpu":
            index_url = "https://download.pytorch.org/whl/cpu"
        else:
            index_url = f"https://download.pytorch.org/whl/{torch_ver}"

        self.torch_version = torch_ver

        # Python 3.13 需要 PyTorch 2.5.0+（2.4.x 不支持 cp313）
        torch_version_spec = "torch>=2.5.0"
        cmd = [
            sys.executable, "-m", "uv", "pip", "install", torch_version_spec,
            "--index-url", index_url
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=600,
                cwd=str(self.project_root)
            )
            return result.returncode == 0
        except Exception:
            return False

    def _install_project_dependencies(self) -> bool:
        """安装项目依赖（包含 ML 可选依赖）"""
        # 使用 uv pip install -e .[ml] 以 editable 模式安装项目 + ML 依赖
        # 这样 python -m mediafactory 才能正常工作
        cmd = [sys.executable, "-m", "uv", "pip", "install", "-e", ".[ml]"]

        if self.use_china_mirror:
            cmd.extend(["--index-url", "https://pypi.tuna.tsinghua.edu.cn/simple"])

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300,
                cwd=str(self.project_root)
            )
            if result.returncode != 0:
                return False
        except Exception:
            return False

        # 如果是开发者，额外安装开发依赖 (使用 uv sync --group dev)
        if self.is_developer:
            dev_cmd = [sys.executable, "-m", "uv", "sync", "--group", "dev"]
            if self.use_china_mirror:
                os.environ["UV_INDEX_URL"] = "https://pypi.tuna.tsinghua.edu.cn/simple"
            try:
                result = subprocess.run(
                    dev_cmd, capture_output=True, text=True, timeout=300,
                    cwd=str(self.project_root)
                )
                # 开发依赖安装失败不阻止整体流程
            except Exception:
                pass

        return True

    def _download_models(self) -> None:
        """下载预定义的模型"""
        print_info("正在下载模型...")

        download_source = "https://hf-mirror.com" if self.use_china_mirror else "https://huggingface.co"

        for model_id in self.PRESET_MODELS:
            print_info(f"检查模型: {model_id}")

            if self._check_model_exists(model_id):
                print_success(f"{model_id} 已存在，跳过")
                continue

            print_info(f"正在下载: {model_id}")

            cmd = [
                sys.executable,
                str(self.project_root / "scripts" / "utils" / "download_model.py"),
                model_id,
                f"--source={download_source}"
            ]

            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=1800,
                    cwd=str(self.project_root)
                )
                if result.returncode == 0:
                    print_success(f"{model_id} 下载完成")
                else:
                    print_warning(f"{model_id} 下载可能存在问题")
            except Exception:
                print_warning(f"{model_id} 下载异常")

    def _check_model_exists(self, huggingface_id: str) -> bool:
        """检查模型是否已存在且完整"""
        model_path = self.project_root / "models" / huggingface_id
        if not model_path.exists():
            return False

        key_files = ["config.json", "model.bin", "pytorch_model.bin", "model.safetensors"]
        for f in key_files:
            if (model_path / f).exists():
                return True
        return False

    def show_completion(self, skip_setup: bool = False) -> None:
        """显示完成信息"""
        print_header("环境初始化完成！")

        if skip_setup:
            print_info("您的环境已经配置完成")
        else:
            print_success("所有依赖已安装")

        print()
        print_info("后续步骤：")
        print("    • 启动应用: python -m mediafactory")
        if self.is_developer:
            print("    • 运行测试: uv run pytest")
        print("    • 查看文档: README.md")
        print()

        # 显示环境摘要
        print_section("环境摘要")
        print(f"  • Python: {sys.version.split()[0]}")
        print(f"  • 用户角色: {'开发者' if self.is_developer else '使用者'}")
        print(f"  • 下载源: {'国内镜像' if self.use_china_mirror else '官方源'}")
        if self.torch_version:
            print(f"  • PyTorch: {self.torch_version}")
        if self.gpu_info:
            print(f"  • GPU: {self.gpu_info[0]['name'] if self.gpu_info else '未检测到'}")
        print()


def main():
    """主函数"""
    # 检查是否在项目根目录
    project_root = Path(__file__).parent.parent
    if not (project_root / "pyproject.toml").exists():
        print_error("请在 MediaFactory 项目根目录下运行此脚本")
        print_info("正确用法: python scripts/setup_env.py")
        sys.exit(1)

    # 检查 Python 版本
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 10):
        print_error(f"需要 Python 3.10+，当前版本: {major}.{minor}")
        sys.exit(1)

    # 运行向导
    wizard = SetupWizard()
    success = wizard.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
