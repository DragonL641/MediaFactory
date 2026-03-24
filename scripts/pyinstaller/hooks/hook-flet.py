"""
PyInstaller hook for Flet framework

Collects Flet framework files for frozen application.
"""

from PyInstaller.utils.hooks import collect_data_files

# 收集 Flet 框架数据文件
datas = collect_data_files('flet')

# 收集 Flet Desktop 可执行文件和依赖（flet.exe, DLLs 等）
datas += collect_data_files('flet_desktop', include_py_files=False)
