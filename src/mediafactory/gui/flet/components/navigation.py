"""
横向导航栏组件

提供顶部页签导航，用于在 Tasks/Models/LLM Config 页面之间切换。
"""

from typing import Callable, Optional
import flet as ft

from mediafactory.gui.flet.theme import get_theme


# 导航项定义 - 更短的名称
NAV_ITEMS = [
    {"id": "tasks", "icon": ft.Icons.ASSIGNMENT_OUTLINED, "label": "Tasks"},
    {"id": "models", "icon": ft.Icons.DOWNLOAD_OUTLINED, "label": "Local Models"},
    {"id": "llm_config", "icon": ft.Icons.CLOUD_OUTLINED, "label": "Remote LLMs"},
]


class TopNavigation:
    """
    横向导航栏组件

    使用顶部页签导航，支持高亮当前选中项。
    """

    def __init__(
        self,
        on_navigate: Callable[[str], None],
        current_page: str = "tasks",
    ):
        """
        初始化导航栏

        Args:
            on_navigate: 导航回调函数，接收页面ID作为参数
            current_page: 当前选中的页面ID
        """
        self.on_navigate = on_navigate
        self._current_page = current_page
        self._component: Optional[ft.Control] = None
        self._nav_buttons: dict = {}

    def build(self) -> ft.Control:
        """构建导航栏组件"""
        theme = get_theme()

        # 导航页签
        nav_controls = []
        for item in NAV_ITEMS:
            btn = self._build_nav_tab(item)
            self._nav_buttons[item["id"]] = btn
            nav_controls.append(btn)

        # 主布局
        self._component = ft.Container(
            content=ft.Row(
                controls=nav_controls,
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            height=48,
            bgcolor=theme.color_scheme.surface,
            border=ft.border.only(
                bottom=ft.BorderSide(1, theme.color_scheme.outline_variant)
            ),
            padding=ft.padding.only(left=8),
        )

        return self._component

    def _build_nav_tab(self, item: dict) -> ft.Control:
        """构建导航页签"""
        theme = get_theme()
        is_selected = item["id"] == self._current_page

        # 根据选中状态设置颜色
        if is_selected:
            bg_color = "transparent"
            icon_color = theme.color_scheme.primary
            text_color = theme.color_scheme.primary
            text_weight = ft.FontWeight.W_600
            indicator_color = theme.color_scheme.primary
        else:
            bg_color = "transparent"
            icon_color = theme.color_scheme.on_surface_variant
            text_color = theme.color_scheme.on_surface_variant
            text_weight = ft.FontWeight.NORMAL
            indicator_color = "transparent"

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(item["icon"], size=18, color=icon_color),
                            ft.Text(
                                item["label"],
                                size=14,
                                weight=text_weight,
                                color=text_color,
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Container(
                        height=3,
                        bgcolor=indicator_color,
                        border_radius=3,
                    ),
                ],
                spacing=0,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
            bgcolor=bg_color,
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
        theme = get_theme()
        if e.data == "true" and page_id != self._current_page:
            # 悬停时设置文字颜色
            e.control.content.controls[0].controls[0].color = theme.color_scheme.on_surface
            e.control.content.controls[0].controls[1].color = theme.color_scheme.on_surface
        elif page_id != self._current_page:
            e.control.content.controls[0].controls[0].color = theme.color_scheme.on_surface_variant
            e.control.content.controls[0].controls[1].color = theme.color_scheme.on_surface_variant
        e.control.update()

    def _update_selection(self) -> None:
        """更新选中状态"""
        theme = get_theme()

        for item in NAV_ITEMS:
            btn = self._nav_buttons.get(item["id"])
            if not btn:
                continue

            is_selected = item["id"] == self._current_page

            # 更新图标颜色
            btn.content.controls[0].controls[0].color = (
                theme.color_scheme.primary if is_selected else theme.color_scheme.on_surface_variant
            )
            # 更新文字颜色和字重
            btn.content.controls[0].controls[1].color = (
                theme.color_scheme.primary if is_selected else theme.color_scheme.on_surface_variant
            )
            btn.content.controls[0].controls[1].weight = (
                ft.FontWeight.W_600 if is_selected else ft.FontWeight.NORMAL
            )
            # 更新底部指示器
            btn.content.controls[1].bgcolor = (
                theme.color_scheme.primary if is_selected else "transparent"
            )

            btn.update()

    def set_current_page(self, page_id: str) -> None:
        """设置当前页面"""
        self._current_page = page_id
        self._update_selection()


def create_navigation(
    on_navigate: Callable[[str], None],
    current_page: str = "tasks",
) -> TopNavigation:
    """创建导航栏的工厂函数"""
    return TopNavigation(on_navigate=on_navigate, current_page=current_page)


# 保留 Sidebar 别名以兼容旧代码
Sidebar = TopNavigation
create_sidebar = create_navigation
