"""
PyInstaller hook for Flet framework

Collects Flet framework files for frozen application.
"""

from PyInstaller.utils.hooks import collect_data_files

# 收集 Flet 框架数据文件
datas = collect_data_files('flet')
