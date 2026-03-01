"""
状态横幅组件

显示成功/错误/警告/信息状态提示。
"""

from enum import Enum
from typing import Optional, Callable
import threading
import time

import flet as ft

from mediafactory.gui.flet.theme import get_theme


class BannerType(Enum):
    """横幅类型"""

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class StatusBanner:
    """
    状态横幅组件

    显示可自动消失的状态提示。
    """

    def __init__(
        self,
        message: str,
        banner_type: BannerType = BannerType.INFO,
        action_text: Optional[str] = None,
        on_action: Optional[Callable[[], None]] = None,
        on_dismiss: Optional[Callable[[], None]] = None,
        duration: int = 5000,  # 自动消失时间（毫秒），0 表示不自动消失
    ):
        self.message = message
        self.banner_type = banner_type
        self.action_text = action_text
        self.on_action = on_action
        self.on_dismiss = on_dismiss
        self.duration = duration

        self._component: Optional[ft.Banner] = None

    def _get_colors(self) -> tuple:
        """获取颜色配置"""
        theme = get_theme()
        colors = {
            BannerType.SUCCESS: (
                theme.color_scheme.tertiary_container,
                theme.color_scheme.on_tertiary_container,
                ft.Icons.CHECK_CIRCLE_OUTLINE,
            ),
            BannerType.ERROR: (
                theme.color_scheme.error_container,
                theme.color_scheme.on_error_container,
                ft.Icons.ERROR_OUTLINE,
            ),
            BannerType.WARNING: (
                "#FFF3E0",  # Warning yellow
                "#E65100",
                ft.Icons.WARNING_AMBER_OUTLINED,
            ),
            BannerType.INFO: (
                theme.color_scheme.primary_container,
                theme.color_scheme.on_primary_container,
                ft.Icons.INFO_OUTLINE,
            ),
        }
        return colors.get(self.banner_type, colors[BannerType.INFO])

    def build(self) -> ft.Banner:
        """构建组件"""
        bgcolor, color, icon = self._get_colors()

        actions = []
        if self.action_text:
            actions.append(
                ft.TextButton(
                    content=self.action_text,
                    on_click=lambda e: self.on_action() if self.on_action else None,
                    style=ft.ButtonStyle(color=color),
                )
            )
        actions.append(
            ft.IconButton(
                icon=ft.Icons.CLOSE,
                icon_color=color,
                on_click=lambda e: self.dismiss(),
            )
        )

        self._component = ft.Banner(
            bgcolor=bgcolor,
            leading=ft.Icon(icon, color=color, size=32),
            content=ft.Text(
                self.message,
                color=color,
                size=14,
            ),
            actions=actions,
        )

        return self._component

    def dismiss(self) -> None:
        """关闭横幅"""
        try:
            if self._component:
                page = self._component.page
                if page:
                    page.banner = None
                    page.update()
        except RuntimeError:
            # 组件已从页面移除，忽略
            pass

        if self.on_dismiss:
            self.on_dismiss()

    def show(self, page: ft.Page) -> None:
        """显示横幅"""
        page.banner = self.build()
        page.update()

        # 自动消失
        if self.duration > 0:

            def auto_dismiss():
                time.sleep(self.duration / 1000)
                try:
                    if self._component:
                        self.dismiss()
                except Exception:
                    pass  # 忽略任何异常

            thread = threading.Thread(target=auto_dismiss, daemon=True)
            thread.start()


def show_success(page: ft.Page, message: str, duration: int = 5000) -> None:
    """显示成功提示"""
    banner = StatusBanner(message, BannerType.SUCCESS, duration=duration)
    banner.show(page)


def show_error(page: ft.Page, message: str, duration: int = 8000) -> None:
    """显示错误提示"""
    banner = StatusBanner(message, BannerType.ERROR, duration=duration)
    banner.show(page)


def show_warning(page: ft.Page, message: str, duration: int = 6000) -> None:
    """显示警告提示"""
    banner = StatusBanner(message, BannerType.WARNING, duration=duration)
    banner.show(page)


def show_info(page: ft.Page, message: str, duration: int = 5000) -> None:
    """显示信息提示"""
    banner = StatusBanner(message, BannerType.INFO, duration=duration)
    banner.show(page)
