"""PyInstaller runtime hook for transformers.

设置 transformers 缓存目录，"""

import os
import sys
import tempfile

# 获取应用根目录
if getattr(sys, 'frozen', False):
    app_root = os.path.dirname(sys.executable)
else:
    app_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# 设置缓存目录
cache_dir = os.path.join(app_root, "cache")

try:
    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(os.path.join(cache_dir, "hub"), exist_ok=True)
except OSError:
    # 权限错误时回退到临时目录
    cache_dir = os.path.join(tempfile.gettempdir(), "mediafactory_cache")
    os.makedirs(cache_dir, exist_ok=True)

# 只设置推荐的环境变量（HF_HOME 是 transformers 5.x 推荐的方式）
os.environ['HF_HOME'] = cache_dir
os.environ['HF_HUB_CACHE'] = os.path.join(cache_dir, "hub")
