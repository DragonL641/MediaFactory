"""
页面模块

包含应用的主要页面。
"""

from mediafactory.gui.flet.pages.tasks import build_tasks_page
from mediafactory.gui.flet.pages.settings import build_settings_page

__all__ = [
    "build_tasks_page",
    "build_settings_page",
]
