# -*- mode: python ; coding: utf-8 -*-
"""
MediaFactory PyInstaller 配置

完整打包所有依赖（包括 ML 依赖）。
输出: onedir 目录模式（macOS 额外生成 .app bundle）
"""

import glob
import os
import platform
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

ML_PACKAGES = [
    'torch',
    'transformers',
    'tokenizers',
    'huggingface_hub',
    'faster_whisper',
    'accelerate',
    'safetensors',
    'sentencepiece',
    'spandrel',
    'gguf',
]

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

    # collect_all 返回空结果时，尝试备用方案
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
# 路径与版本
# =============================================================================

BASE_DIR = (Path(SPECPATH) / ".." / "..").resolve()
DIST_DIR = BASE_DIR / "dist"
IS_MACOS = platform.system() == 'Darwin'

# 版本号：优先环境变量，统一从 _version.py 获取
sys.path.insert(0, str(BASE_DIR / "src"))
from mediafactory._version import get_version

APP_VERSION = os.environ.get("APP_VERSION", get_version())
PROJECT_NAME = "MediaFactory"

# Icon
_icon_path = {
    "darwin": BASE_DIR / "src" / "mediafactory" / "resources" / "icon.icns",
    "windows": BASE_DIR / "src" / "mediafactory" / "resources" / "icon.ico",
}.get(platform.system().lower())
ICON_PATH = str(_icon_path) if _icon_path and _icon_path.exists() else None

# =============================================================================
# 数据文件
# =============================================================================

datas = [
    (str(BASE_DIR / "pyproject.toml"), "."),  # _version.py 需要读取版本号
    (str(BASE_DIR / "config.toml.example"), "."),
    (str(BASE_DIR / "src" / "mediafactory" / "resources"), "mediafactory/resources"),
    (str(BASE_DIR / "NOTICE.txt"), "."),
    (str(BASE_DIR / "THIRD_PARTY_LICENSES.txt"), "."),
]

# =============================================================================
# mypyc 编译模块
# =============================================================================

binaries = []
if platform.system() == 'Windows':
    site_packages = Path(sys.prefix) / "Lib" / "site-packages"
    mypyc_pattern = "*__mypyc*.pyd"
else:
    python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    site_packages = Path(sys.prefix) / "lib" / python_version / "site-packages"
    mypyc_pattern = "*__mypyc*.so"

for mypyc_file in glob.glob(str(site_packages / mypyc_pattern)):
    binaries.append((mypyc_file, "."))
    print(f"[INFO] Collected mypyc module: {Path(mypyc_file).name}")

# =============================================================================
# 隐藏导入
# =============================================================================

hiddenimports = [
    # 主应用程序
    'mediafactory.api',
    'mediafactory.api.main',
    'mediafactory.api.routes',
    'mediafactory.api.routes.config',
    'mediafactory.api.routes.models',
    'mediafactory.api.routes.processing',
    'mediafactory.api.schemas',
    'mediafactory.api.websocket',
    'mediafactory.api.task_manager',
    'mediafactory.api.task_executor',
    'mediafactory.services',
    'mediafactory.core',
    'mediafactory.config',
    'mediafactory.pipeline',
    # Uvicorn（ASGI 服务器）
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
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
    # HuggingFace 生态
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
    # PyTorch
    'torch',
    # pkg_resources
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

EXCLUDES = [
    'pytest', 'black', 'mypy', 'pylint', 'flake8', 'pre_commit',
    'pip', 'setuptools', 'wheel', 'build', 'twine',
]

# =============================================================================
# 分析
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

strip = False
pyz = PYZ(a.pure, a.zipped_data)

# =============================================================================
# 输出（所有平台共用 EXE + COLLECT，macOS 额外加 BUNDLE）
# =============================================================================

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

# macOS: 额外创建 .app bundle
if IS_MACOS:
    app = BUNDLE(
        coll,
        name=f"{PROJECT_NAME}.app",
        icon=ICON_PATH,
        bundle_identifier="com.mediafactory.app",
        info_plist={
            'CFBundleName': PROJECT_NAME,
            'CFBundleDisplayName': PROJECT_NAME,
            'CFBundleVersion': APP_VERSION,
            'CFBundleShortVersionString': APP_VERSION,
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '10.13',
        },
    )
