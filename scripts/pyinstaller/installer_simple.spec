# -*- mode: python ; coding: utf-8 -*-
"""
MediaFactory PyInstaller 配置

完整打包所有依赖（包括 ML 依赖）。

输出:
- Windows: onedir 目录模式
- macOS: app bundle
"""

import os
import platform
import subprocess
import sys
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_all,
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

# =============================================================================
# 收集 ML 依赖
# =============================================================================

# 需要完整收集的 ML 包
ML_PACKAGES = [
    'torch',
    'transformers',
    'tokenizers',
    'huggingface_hub',
    'faster_whisper',
    'accelerate',
    'safetensors',
]

# 收集所有 ML 包的文件
ml_datas = []
ml_binaries = []
ml_hiddenimports = []

for pkg in ML_PACKAGES:
    collected = False
    try:
        pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(pkg)
        if pkg_datas or pkg_binaries or pkg_hiddenimports:
            ml_datas.extend(pkg_datas)
            ml_binaries.extend(pkg_binaries)
            ml_hiddenimports.extend(pkg_hiddenimports)
            print(f"[INFO] collect_all({pkg}): {len(pkg_datas)} datas, {len(pkg_binaries)} binaries, {len(pkg_hiddenimports)} hiddenimports")
            collected = True
    except Exception as e:
        print(f"[WARN] collect_all({pkg}) failed: {e}")

    # 如果 collect_all 返回空结果，尝试备用方案
    if not collected:
        try:
            pkg_datas = collect_data_files(pkg)
            pkg_binaries = collect_dynamic_libs(pkg)
            pkg_hiddenimports = collect_submodules(pkg)
            if pkg_datas:
                ml_datas.extend(pkg_datas)
            if pkg_binaries:
                ml_binaries.extend(pkg_binaries)
            if pkg_hiddenimports:
                ml_hiddenimports.extend(pkg_hiddenimports)
            print(f"[INFO] Fallback collected {pkg}: {len(pkg_datas)} datas, {len(pkg_binaries)} binaries, {len(pkg_hiddenimports)} hiddenimports")
        except Exception as e:
            print(f"[ERROR] Failed to collect {pkg}: {e}")

# =============================================================================
# 配置
# =============================================================================

# Base paths
BASE_DIR = Path(SPECPATH) / ".." / ".."
BASE_DIR = BASE_DIR.resolve()
DIST_DIR = BASE_DIR / "dist"

# Platform detection
IS_MACOS = platform.system() == 'Darwin'
IS_WINDOWS = platform.system() == 'Windows'
IS_LINUX = platform.system() == 'Linux'

# Version (from environment or _version.py)
def _get_version_from_pyproject() -> str:
    """从 _version.py 获取版本号（统一版本源）"""
    version_script = BASE_DIR / "src" / "mediafactory" / "_version.py"

    if version_script.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(version_script)],
                capture_output=True,
                text=True,
                cwd=str(BASE_DIR),
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                if version:
                    return version
        except Exception:
            pass

    # 回退：直接解析 pyproject.toml（最后手段）
    pyproject_path = BASE_DIR / "pyproject.toml"
    if pyproject_path.exists():
        content = pyproject_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.startswith("version = "):
                return line.split('"')[1]
    return "0.2.0"  # 回退版本

APP_VERSION = os.environ.get("APP_VERSION", _get_version_from_pyproject())
PROJECT_NAME = "MediaFactory"

# Icon paths
ICON_PATHS = {
    "darwin": BASE_DIR / "src" / "mediafactory" / "resources" / "icon.icns",
    "windows": BASE_DIR / "src" / "mediafactory" / "resources" / "icon.ico",
}
ICON_PATH = str(ICON_PATHS.get(platform.system().lower())) if Path(ICON_PATHS.get(platform.system().lower(), "")).exists() else None

# =============================================================================
# 数据文件
# =============================================================================

datas = [
    # 配置文件示例
    (str(BASE_DIR / "config.toml.example"), "."),
    # 资源文件
    (str(BASE_DIR / "src" / "mediafactory" / "resources"), "mediafactory/resources"),
    # 许可证文件（法律合规要求）
    (str(BASE_DIR / "NOTICE.txt"), "."),
    (str(BASE_DIR / "THIRD_PARTY_LICENSES.txt"), "."),
]

# =============================================================================
# 收集 mypyc 编译的模块
# =============================================================================

import glob

binaries = []
site_packages = Path(sys.prefix) / "Lib" / "site-packages"
for mypyc_file in glob.glob(str(site_packages / "*__mypyc*.pyd")):
    binaries.append((mypyc_file, "."))

# =============================================================================
# 隐藏导入
# =============================================================================

hiddenimports = [
    # 主应用程序
    'mediafactory.gui',
    'mediafactory.gui.main_window',
    'mediafactory.core',
    'mediafactory.config',
    'mediafactory.pipeline',
    # 配置和日志
    'loguru',
    'pydantic',
    'pydantic_settings',
    'pydantic_core',
    'tomli',
    'tomli_w',
    # FFmpeg
    'ffmpeg',
    'imageio_ffmpeg',
    # 进度显示
    'tqdm',
    # 语言检测
    'langdetect',
    # LLM API SDKs
    'openai',
    # HuggingFace 生态（模型下载和运行）
    'huggingface_hub',
    'huggingface_hub.utils',
    'huggingface_hub.file_download',
    'transformers',
    'transformers.utils',
    'transformers.models',
    'tokenizers',
    'safetensors',
    'accelerate',
    # Whisper 生态
    'faster_whisper',
    'faster_whisper.transcribe',
    'faster_whisper.download_model',
    # PyTorch（faster-whisper 依赖）
    'torch',
    # pkg_resources（修复 pyi_rth_pkgres 错误）
    'importlib_metadata',
    'importlib_resources',
    'packaging',
    'packaging.requirements',
    'pkg_resources',
    'pkg_resources._vendor',
    # Windows specific
    '_distutils_hack',
    'distutils',
]

# =============================================================================
# 排除的模块（仅开发工具）
# =============================================================================

DEV_EXCLUDES = [
    'pytest', 'black', 'mypy', 'pylint', 'flake8', 'pre_commit',
    'pip', 'setuptools', 'wheel', 'build', 'twine',
]

EXCLUDES = DEV_EXCLUDES

# =============================================================================
# 分析配置
# =============================================================================

a = Analysis(
    [str(BASE_DIR / "src" / "mediafactory" / "__main__.py")],
    pathex=[str(DIST_DIR), str(BASE_DIR / "src")],
    binaries=binaries + ml_binaries,
    datas=datas + ml_datas,
    hiddenimports=hiddenimports + ml_hiddenimports,
    hookspath=[str(BASE_DIR / "scripts" / "pyinstaller" / "hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# 移除 .DS_Store 文件
a.binaries = [x for x in a.binaries if '.DS_Store' not in str(x[0])]
a.datas = [x for x in a.datas if '.DS_Store' not in str(x[0])]

# Strip 符号（禁用 - Windows 上没有 strip 工具）
strip = False

# PYZ 加密
pyz = PYZ(a.pure, a.zipped_data)

# =============================================================================
# 平台特定配置
# =============================================================================

if IS_WINDOWS:
    # Windows: onedir 目录模式
    exe = EXE(
        pyz,
        a.scripts,
        exclude_binaries=True,
        name=PROJECT_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=strip,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=ICON_PATH,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=strip,
        upx=False,
        upx_exclude=[],
        name=PROJECT_NAME,
    )

elif IS_MACOS:
    # macOS: app bundle
    exe = EXE(
        pyz,
        a.scripts,
        exclude_binaries=True,
        name=PROJECT_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=strip,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=ICON_PATH,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=strip,
        upx=False,
        upx_exclude=[],
        name=PROJECT_NAME,
    )

    # 创建 app bundle
    app = BUNDLE(
        coll,
        name=f"{PROJECT_NAME}.app",
        icon=ICON_PATH,
        bundle_identifier=f"com.mediafactory.app",
        info_plist={
            'CFBundleName': PROJECT_NAME,
            'CFBundleDisplayName': PROJECT_NAME,
            'CFBundleVersion': APP_VERSION,
            'CFBundleShortVersionString': APP_VERSION,
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '10.13',
        },
    )

else:
    # Linux: 目录输出
    exe = EXE(
        pyz,
        a.scripts,
        exclude_binaries=True,
        name=PROJECT_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=strip,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=ICON_PATH,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=strip,
        upx=False,
        upx_exclude=[],
        name=PROJECT_NAME,
    )
