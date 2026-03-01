"""
侧边栏导航组件

提供垂直导航栏，用于在工具/模型/设置页面之间切换。
"""

from typing import Callable, Optional, List
import flet as ft

from mediafactory.gui.flet.theme import get_theme


# 导航项定义
NAV_ITEMS = [
    {"id": "tasks", "icon": ft.Icons.ASSIGNMENT_OUTLINED, "label": "Tasks"},
    {"id": "settings", "icon": ft.Icons.SETTINGS_OUTLINED, "label": "Settings"},
]


class Sidebar:
    """
    侧边栏导航组件

    使用固定宽度(160px)的垂直导航栏，支持高亮当前选中项。
    """

    def __init__(
        self,
        on_navigate: Callable[[str], None],
        current_page: str = "tools",
    ):
        """
        初始化侧边栏

        Args:
            on_navigate: 导航回调函数，接收页面ID作为参数
            current_page: 当前选中的页面ID
        """
        self.on_navigate = on_navigate
        self._current_page = current_page
        self._component: Optional[ft.Control] = None
        self._nav_buttons: dict = {}

    def build(self) -> ft.Control:
        """构建侧边栏组件"""
        theme = get_theme()

        # 应用标题
        header = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.VIDEO_LIBRARY,
                        size=24,
                        color=theme.color_scheme.primary,
                    ),
                    ft.Text(
                        "MediaFactory",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=theme.color_scheme.on_surface,
                    ),
                ],
                spacing=10,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(vertical=20, horizontal=10),
        )

        # 导航按钮
        nav_controls = []
        for item in NAV_ITEMS:
            btn = self._build_nav_button(item)
            self._nav_buttons[item["id"]] = btn
            nav_controls.append(btn)

        # 导航区域
        nav_section = ft.Column(
            controls=nav_controls,
            spacing=4,
        )

        # 主布局
        self._component = ft.Container(
            content=ft.Column(
                controls=[
                    header,
                    ft.Divider(color=theme.color_scheme.outline_variant, height=1),
                    ft.Container(height=10),
                    nav_section,
                ],
                spacing=0,
            ),
            width=160,
            bgcolor=theme.color_scheme.surface,
            border=ft.border.only(
                right=ft.BorderSide(1, theme.color_scheme.outline_variant)
            ),
            padding=0,
        )

        return self._component

    def _build_nav_button(self, item: dict) -> ft.Control:
        """构建导航按钮"""
        theme = get_theme()
        is_selected = item["id"] == self._current_page

        # 根据选中状态设置颜色
        if is_selected:
            bg_color = theme.color_scheme.primary_container
            icon_color = theme.color_scheme.primary
            text_color = theme.color_scheme.primary
            text_weight = ft.FontWeight.W_600
        else:
            bg_color = "transparent"
            icon_color = theme.color_scheme.on_surface_variant
            text_color = theme.color_scheme.on_surface_variant
            text_weight = ft.FontWeight.NORMAL

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(item["icon"], size=20, color=icon_color),
                    ft.Text(
                        item["label"],
                        size=14,
                        weight=text_weight,
                        color=text_color,
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            bgcolor=bg_color,
            border_radius=theme.radius_md,
            on_click=lambda e, page_id=item["id"]: self._on_nav_click(page_id),
            on_hover=lambda e, page_id=item["id"]: self._on_hover(e, page_id),
            ink=True,
        )

    def _on_nav_click(self, page_id: str) -> None:
        """导航点击事件"""
        if page_id != self._current_page:
            self._current_page = page_id
            self._update_selection()
            if self.on_navigate:
                self.on_navigate(page_id)

    def _on_hover(self, e, page_id: str) -> None:
        """悬停事件"""
        if e.data == "true" and page_id != self._current_page:
            e.control.bgcolor = e.control.theme.color_scheme.surface_variant
        elif page_id != self._current_page:
            e.control.bgcolor = "transparent"
        e.control.update()

    def _update_selection(self) -> None:
        """更新选中状态"""
        theme = get_theme()

        for item in NAV_ITEMS:
            btn = self._nav_buttons.get(item["id"])
            if not btn:
                continue

            is_selected = item["id"] == self._current_page

            if is_selected:
                btn.bgcolor = theme.color_scheme.primary_container
                btn.content.controls[0].color = theme.color_scheme.primary
                btn.content.controls[1].color = theme.color_scheme.primary
                btn.content.controls[1].weight = ft.FontWeight.W_600
            else:
                btn.bgcolor = "transparent"
                btn.content.controls[0].color = theme.color_scheme.on_surface_variant
                btn.content.controls[1].color = theme.color_scheme.on_surface_variant
                btn.content.controls[1].weight = ft.FontWeight.NORMAL

            btn.update()

    def set_current_page(self, page_id: str) -> None:
        """设置当前页面"""
        self._current_page = page_id
        self._update_selection()


def create_sidebar(
    on_navigate: Callable[[str], None],
    current_page: str = "tasks",
) -> Sidebar:
    """创建侧边栏的工厂函数"""
    return Sidebar(on_navigate=on_navigate, current_page=current_page)
