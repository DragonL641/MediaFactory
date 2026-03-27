# -*- coding: utf-8 -*-
"""
PyInstaller hook for uvicorn

确保 uvicorn 及其依赖被正确收集
"""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# 收集 uvicorn 所有子模块
hiddenimports = collect_submodules("uvicorn")

# 收集 uvicorn 数据文件
datas = collect_data_files("uvicorn")
