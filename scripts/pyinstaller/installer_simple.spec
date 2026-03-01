# -*- mode: python ; coding: utf-8 -*-
"""
MediaFactory 简化 PyInstaller 配置

核心设计原则:
1. 仅打包启动依赖（GUI、配置、日志等）
2. 不打包 ML 依赖（torch, transformers, faster-whisper）
3. 首次启动时通过 Setup Wizard 下载模型和依赖

输出:
- Windows: --onefile 单文件模式
- macOS: app bundle (默认)
"""

import os
import platform
import sys
from pathlib import Path

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

# Version (from environment or pyproject.toml)
APP_VERSION = os.environ.get("APP_VERSION", "3.1.0")
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
]

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
    # LLM API SDKs（远程翻译，无需本地模型）
    'openai',
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
# 排除的模块（ML 依赖 + 开发工具）
# =============================================================================

# ML 依赖将在首次启动时通过 Setup Wizard 下载
ML_EXCLUDES = [
    # PyTorch 生态
    'torch', 'torchvision', 'torchaudio',
    # Transformers 生态
    'transformers', 'tokenizers', 'huggingface_hub',
    # Whisper 生态
    'faster_whisper', 'whisper', 'openai_whisper',
    # NLP 工具
    'sentencepiece', 'accelerate', 'safetensors', 'protobuf',
    # 编译优化
    'numba', 'torchao',
    # 可选 ML 后端
    'onnxruntime', 'ctranslate2',
    # 其他 ML 库
    'scipy', 'sklearn', 'pandas', 'matplotlib',
]

# 开发工具
DEV_EXCLUDES = [
    'pytest', 'black', 'mypy', 'pylint', 'flake8', 'pre_commit',
    'pip', 'setuptools', 'wheel', 'build', 'twine',
]

EXCLUDES = ML_EXCLUDES + DEV_EXCLUDES

# =============================================================================
# 分析配置
# =============================================================================

a = Analysis(
    [str(BASE_DIR / "src" / "mediafactory" / "__main__.py")],
    pathex=[str(DIST_DIR), str(BASE_DIR / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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

# Strip 符号（macOS 除外）
strip = not IS_MACOS

# PYZ 加密
pyz = PYZ(a.pure, a.zipped_data)

# =============================================================================
# 可执行文件配置
# =============================================================================

exe_kwargs = {
    'pyz': pyz,
    'a.scripts': a.scripts,
    'exclude_binaries': False,
    'name': PROJECT_NAME,
    'debug': False,
    'bootloader_ignore_signals': False,
    'strip': strip,
    'upx': False,
    'console': False,  # 无控制台窗口
    'disable_windowed_traceback': False,
    'argv_emulation': False,
    'target_arch': None,
    'codesign_identity': None,
    'entitlements_file': None,
}

if ICON_PATH:
    exe_kwargs['icon'] = ICON_PATH

# =============================================================================
# 平台特定配置
# =============================================================================

if IS_WINDOWS:
    # Windows: one-file 单文件模式
    exe_kwargs['exclude_binaries'] = False
    exe = EXE(**exe_kwargs)
    
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=strip,
        upx=False,
        upx_exclude=[],
        name=PROJECT_NAME,
    )
    
    # 将单文件输出到 dist 根目录
    EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
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

elif IS_MACOS:
    # macOS: app bundle
    exe_kwargs['exclude_binaries'] = True
    exe = EXE(**exe_kwargs)
    
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
    # Linux: 标准目录输出
    exe = EXE(**exe_kwargs)
    
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=strip,
        upx=False,
        upx_exclude=[],
        name=PROJECT_NAME,
    )
