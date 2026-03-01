"""Transformers 库配置模块。

此模块在应用启动时最早被调用，用于设置 transformers 的缓存目录
到一个可写位置，避免 PyInstaller 打包后的权限问题。
"""

import os
import sys
from pathlib import Path


def setup_transformers_cache():
    """设置 Transformers 库的缓存目录。

    在 PyInstaller 打包的环境中，transformers 的默认缓存目录可能不存在
    或不可写。此函数将缓存目录设置到应用根目录下的 cache 文件夹。

    此函数必须在导入 transformers 之前调用。
    """
    try:
        # 获取应用根目录
        if getattr(sys, "frozen", False):
            # PyInstaller 打包后的环境
            if hasattr(sys, "_MEIPASS"):
                # --onefile 模式
                app_root = Path(sys.executable).parent
            else:
                # --onedir 模式
                app_root = Path(sys.executable).parent
        else:
            # 开发环境
            app_root = Path(__file__).parent.parent.parent.resolve()

        # 创建缓存目录
        cache_dir = app_root / "cache"
        cache_dir.mkdir(exist_ok=True)

        # 设置 transformers 相关的环境变量（TRANSFORMERS_CACHE 已在 v5 中弃用，只使用 HF_HOME）
        os.environ["HF_HOME"] = str(cache_dir)
        os.environ["HF_HUB_CACHE"] = str(cache_dir / "hub")
        os.environ["HUGGINGFACE_HUB_CACHE"] = str(cache_dir / "hub")

        # 确保所有子目录都存在
        (cache_dir / "hub").mkdir(exist_ok=True)
        (cache_dir / "models").mkdir(exist_ok=True)

        return cache_dir
    except Exception:
        # 静默处理错误，避免在打包后打印到控制台
        pass
    return None


# 模块加载时自动执行配置
# 注意：不要在模块级别执行，而是在需要时显式调用
# 以避免在导入时就可能产生的副作用
_CACHE_DIR = None


def ensure_cache_setup():
    """确保缓存已设置（懒加载方式）。"""
    global _CACHE_DIR
    if _CACHE_DIR is None:
        _CACHE_DIR = setup_transformers_cache()
    return _CACHE_DIR
