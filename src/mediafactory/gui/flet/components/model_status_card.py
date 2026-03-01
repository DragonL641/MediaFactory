"""
模型状态卡片组件

显示单个模型的加载状态。
"""

from typing import Optional, Callable
import flet as ft

from mediafactory.gui.flet.theme import get_theme
from mediafactory.gui.flet.state import ModelStatus


class ModelStatusCard:
    """模型状态卡片组件"""

    def __init__(
        self,
        status: ModelStatus,
        on_click: Optional[Callable[[str], None]] = None,
        on_toggle: Optional[Callable[[str, bool], None]] = None,
    ):
        self.status = status
        self.on_click = on_click
        self.on_toggle = on_toggle  # 仅 LLM 使用
        self.theme = get_theme()
        self._component: Optional[ft.Control] = None
        self._toggle_switch: Optional[ft.Switch] = None

    def build(self) -> ft.Control:
        """构建组件"""
        is_llm = self.status.model_type == "llm"

        # 状态图标和颜色
        if self.status.loaded or self.status.available:
            icon = ft.Icons.CHECK_CIRCLE
            icon_color = self.theme.color_scheme.tertiary
            status_text = "Ready"
        else:
            icon = ft.Icons.RADIO_BUTTON_UNCHECKED
            icon_color = self.theme.color_scheme.outline
            status_text = "Not Loaded"

        # 模型图标
        model_icon = {
            "whisper": ft.Icons.MIC,
            "translation": ft.Icons.TRANSLATE,
            "llm": ft.Icons.CLOUD,
        }.get(self.status.model_type, ft.Icons.STORAGE)

        # 构建内容
        content_controls = [
            # 第一行：图标和名称
            ft.Row(
                controls=[
                    ft.Icon(
                        model_icon, size=20, color=self.theme.color_scheme.on_surface
                    ),
                    ft.Text(
                        self.status.name,
                        size=13,
                        weight=ft.FontWeight.W_500,
                        color=self.theme.color_scheme.on_surface,
                        expand=True,
                    ),
                    ft.Icon(icon, size=16, color=icon_color),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ]

        # LLM 开关
        if is_llm:
            self._toggle_switch = ft.Switch(
                value=self.status.enabled,
                on_change=lambda e: self._on_toggle_click(e.control.value),
                active_color=self.theme.color_scheme.primary,
            )
            content_controls[0].controls.append(self._toggle_switch)

        # 主容器
        self._component = ft.Container(
            content=ft.Column(
                controls=content_controls,
                spacing=4,
            ),
            padding=ft.padding.all(10),
            bgcolor=self.theme.color_scheme.surface_variant,
            border_radius=self.theme.radius_md,
            border=ft.border.all(1, self.theme.color_scheme.outline_variant),
            on_click=lambda e: self._on_click() if self.on_click else None,
            ink=self.on_click is not None,
            opacity=0.5 if is_llm and not self.status.enabled else 1.0,
        )

        return self._component

    def _on_click(self) -> None:
        """点击事件"""
        if self.on_click:
            self.on_click(self.status.model_type)

    def _on_toggle_click(self, value: bool) -> None:
        """开关切换"""
        if self.on_toggle:
            self.on_toggle(self.status.model_type, value)

    def update_status(self, status: ModelStatus) -> None:
        """更新状态"""
        self.status = status
        if self._component:
            self._component.opacity = (
                0.5 if status.model_type == "llm" and not status.enabled else 1.0
            )
            if self._toggle_switch:
                self._toggle_switch.value = status.enabled
            self._component.update()
