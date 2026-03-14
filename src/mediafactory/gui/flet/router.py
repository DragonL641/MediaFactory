"""
路由导航系统

定义路由配置和辅助函数。
注：实际导航逻辑已集成到 app.py 中。
"""

from dataclasses import dataclass
from typing import Callable, Dict, Optional, Any
import flet as ft


@dataclass
class Route:
    """路由定义"""

    path: str
    title: str
    icon: str
    builder: Callable[[ft.Page, Dict[str, Any]], ft.Control]
    meta: Dict[str, Any] = None


# 路由配置（供参考和扩展使用）
ROUTES = [
    Route(
        path="/tasks",
        title="Tasks",
        icon=ft.Icons.ASSIGNMENT_OUTLINED,
        builder=None,  # 在 app.py 中动态加载
    ),
]


def get_route_by_path(path: str) -> Optional[Route]:
    """根据路径获取路由定义"""
    for route in ROUTES:
        if route.path == path:
            return route
    return None


def get_all_routes() -> Dict[str, Route]:
    """获取所有路由"""
    return {route.path: route for route in ROUTES}
