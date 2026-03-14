"""
可复用 UI 组件
"""

from mediafactory.gui.flet.components.status_banner import StatusBanner, BannerType
from mediafactory.gui.flet.components.navigation import TopNavigation, Sidebar, NAV_ITEMS
from mediafactory.gui.flet.components.task_card import TaskCard
from mediafactory.gui.flet.components.task_config_dialog import (
    TaskConfigDialog,
    TASK_TYPES,
    TASK_TYPE_NAMES,
)
# ModelStatusCard 和 ModelStatusSection 已移至 Models 页面

__all__ = [
    "StatusBanner",
    "BannerType",
    "TopNavigation",
    "Sidebar",  # 别名，兼容旧代码
    "NAV_ITEMS",
    "TaskCard",
    "TaskConfigDialog",
    "TASK_TYPES",
    "TASK_TYPE_NAMES",
]
