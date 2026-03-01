"""PyInstaller runtime hook for transformers.

This hook ensures transformers_config is loaded before transformers,
to set up the cache directory properly in the frozen environment.
"""

import os
import sys

# Get the application root directory
if getattr(sys, 'frozen', False):
    if hasattr(sys, '_MEIPASS'):
        app_root = os.path.dirname(sys.executable)
    else:
        app_root = os.path.dirname(sys.executable)
else:
    app_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# Set transformers cache environment variables BEFORE any transformers import
cache_dir = os.path.join(app_root, "cache")
os.makedirs(cache_dir, exist_ok=True)

os.environ['TRANSFORMERS_CACHE'] = cache_dir
os.environ['HF_HOME'] = cache_dir
os.environ['HF_HUB_CACHE'] = os.path.join(cache_dir, "hub")
os.environ['HUGGINGFACE_HUB_CACHE'] = os.path.join(cache_dir, "hub")

# Ensure cache subdirectories exist
os.makedirs(os.path.join(cache_dir, "hub"), exist_ok=True)
os.makedirs(os.path.join(cache_dir, "models"), exist_ok=True)
