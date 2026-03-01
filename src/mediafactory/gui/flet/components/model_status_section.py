"""
模型状态区域组件

纵向三部分布局：
1. Faster Whisper Large V3 状态
2. 本地翻译模型状态（三个档位）
3. 远端 LLM 状态（列表显示所有预设的连通性）
"""

from typing import Optional, Callable, Dict, Any, List
import asyncio
import flet as ft

from mediafactory.gui.flet.theme import get_theme, SEMANTIC_COLORS
from mediafactory.gui.flet.state import ModelStatus
from mediafactory.gui.flet.services import get_model_status_service


class ModelStatusSection:
    """模型状态区域组件 - 纵向三部分布局"""

    def __init__(
        self,
        page: ft.Page,
        whisper_status: Optional[ModelStatus] = None,
        translation_status: Optional[ModelStatus] = None,
        llm_status: Optional[ModelStatus] = None,
        on_model_click: Optional[Callable[[str], None]] = None,
        on_llm_toggle: Optional[Callable[[bool], None]] = None,
    ):
        self.page = page
        self.whisper_status = whisper_status
        self.translation_status = translation_status
        self.llm_status = llm_status
        self.on_model_click = on_model_click
        self.on_llm_toggle = on_llm_toggle
        self.theme = get_theme()
        self.model_service = get_model_status_service()

        self._component: Optional[ft.Control] = None
        self._llm_cards: List[ft.Container] = []
        self._llm_connection_statuses: Dict[str, str] = {}  # preset_id -> status

    def build(self) -> ft.Control:
        """构建组件"""
        self._component = ft.Container(
            content=self._rebuild_content(),
            padding=ft.padding.all(16),
            bgcolor=self.theme.color_scheme.surface,
            border_radius=self.theme.radius_md,
            border=ft.border.all(1, self.theme.color_scheme.outline_variant),
        )

        # 页面加载时自动测试 LLM 连通性
        self._start_initial_llm_test()

        return self._component

    def _rebuild_content(self) -> ft.Column:
        """构建内容部分 - 供 build() 和 _on_refresh_click() 共用"""
        return ft.Column(
            controls=[
                # 标题行（添加刷新按钮）
                ft.Row(
                    controls=[
                        # 左侧图标和标题
                        ft.Row(
                            controls=[
                                ft.Icon(
                                    ft.Icons.DEVICES_OUTLINED,
                                    size=18,
                                    color=self.theme.color_scheme.primary,
                                ),
                                ft.Text(
                                    "Model Status",
                                    size=14,
                                    weight=ft.FontWeight.W_600,
                                    color=self.theme.color_scheme.on_surface,
                                ),
                            ],
                            spacing=8,
                        ),
                        # 右侧刷新按钮
                        ft.IconButton(
                            icon=ft.Icons.REFRESH,
                            icon_size=18,
                            tooltip="Refresh Model Status",
                            on_click=self._on_refresh_click,
                            style=ft.ButtonStyle(
                                color=self.theme.color_scheme.primary,
                            ),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(height=12),
                # 三列布局
                ft.Row(
                    controls=[
                        # 第一列: Whisper
                        ft.Container(
                            content=self._build_whisper_section(),
                            expand=1,
                        ),
                        ft.VerticalDivider(
                            width=1,
                            color=self.theme.color_scheme.outline_variant,
                        ),
                        # 第二列: 本地翻译模型
                        ft.Container(
                            content=self._build_translation_section(),
                            expand=1,
                        ),
                        ft.VerticalDivider(
                            width=1,
                            color=self.theme.color_scheme.outline_variant,
                        ),
                        # 第三列: LLM
                        ft.Container(
                            content=self._build_llm_section(),
                            expand=1,
                        ),
                    ],
                    spacing=16,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
            ],
            spacing=0,
        )

    def _on_refresh_click(self, e) -> None:
        """刷新按钮点击处理"""
        import threading

        def run_refresh():
            try:
                # 调用刷新方法
                self.model_service.refresh_model_status()

                # 获取新状态
                whisper_status = self.model_service.get_whisper_status()
                translation_status = self.model_service.get_translation_status()
                llm_status = self.model_service.get_llm_status()

                # 更新组件状态
                self.whisper_status = whisper_status
                self.translation_status = translation_status
                self.llm_status = llm_status

                # 重新构建组件内容
                if self._component and self.page:
                    self._component.content = self._rebuild_content()

                    # 更新 UI
                    self.page.update()

                    # 显示刷新成功提示
                    self._show_snackbar("Model status refreshed")

            except Exception as ex:
                if self.page:
                    self._show_snackbar(f"Refresh failed: {str(ex)[:50]}", error=True)

        # 在后台线程执行刷新
        thread = threading.Thread(target=run_refresh, daemon=True)
        thread.start()

    def _show_snackbar(self, message: str, error: bool = False) -> None:
        """显示 SnackBar 提示"""
        if not self.page:
            return

        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(
                message,
                color=ft.Colors.WHITE if not error else ft.Colors.BLACK,
            ),
            bgcolor=ft.Colors.GREEN_700 if not error else ft.Colors.RED_400,
            duration=2000,
        )
        self.page.snack_bar.open = True
        self.page.update()

    def _build_whisper_section(self) -> ft.Control:
        """构建 Whisper 状态部分 - 简化版，只显示可用性"""
        # 获取最新状态
        status = self.model_service.get_whisper_status()

        # 状态指示
        if status.available:
            status_icon = ft.Icons.CHECK_CIRCLE
            status_color = SEMANTIC_COLORS["success"]
            status_text = "Available"
        else:
            status_icon = ft.Icons.WARNING_AMBER_ROUNDED
            status_color = SEMANTIC_COLORS["warning"]
            status_text = "Not Available"

        return ft.Column(
            controls=[
                # 标题
                ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.MIC,
                            size=16,
                            color=self.theme.color_scheme.primary,
                        ),
                        ft.Text(
                            "Speech Recognition",
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color=self.theme.color_scheme.on_surface,
                        ),
                    ],
                    spacing=6,
                ),
                ft.Container(height=10),
                # 模型信息卡片（简化版）
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Text(
                                        "Faster Whisper Large V3",
                                        size=12,
                                        weight=ft.FontWeight.W_500,
                                        color=self.theme.color_scheme.on_surface,
                                    ),
                                    ft.Container(height=2),
                                    ft.Text(
                                        (
                                            "Go to Settings to download"
                                            if not status.available
                                            else "Ready to use"
                                        ),
                                        size=10,
                                        color=self.theme.color_scheme.on_surface_variant,
                                        italic=not status.available,
                                    ),
                                ],
                                spacing=0,
                                expand=True,
                            ),
                            ft.Icon(status_icon, size=20, color=status_color),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.padding.all(10),
                    bgcolor=self.theme.color_scheme.surface_variant,
                    border_radius=self.theme.radius_sm,
                ),
            ],
            spacing=0,
        )

    def _build_translation_section(self) -> ft.Control:
        """构建本地翻译模型状态部分 - 简化版，只显示可用性"""
        # 获取三个档位的模型状态
        models = self.model_service.get_translation_model_statuses()

        # 统计下载状态
        downloaded_count = sum(1 for m in models if m["downloaded"])
        any_available = downloaded_count > 0

        model_cards = []
        for model in models:
            if model["downloaded"]:
                status_icon = ft.Icons.CHECK_CIRCLE
                status_color = SEMANTIC_COLORS["success"]
            else:
                status_icon = ft.Icons.REMOVE_CIRCLE_OUTLINE
                status_color = self.theme.color_scheme.outline

            card = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Text(
                            model["name"],
                            size=11,
                            weight=ft.FontWeight.W_500,
                            color=self.theme.color_scheme.on_surface,
                            expand=True,
                        ),
                        ft.Icon(status_icon, size=14, color=status_color),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                bgcolor=self.theme.color_scheme.surface_variant,
                border_radius=self.theme.radius_sm,
            )
            model_cards.append(card)

        # 底部提示
        hint_text = (
            f"{downloaded_count}/3 available"
            if any_available
            else "Go to Settings to download"
        )

        return ft.Column(
            controls=[
                # 标题
                ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.TRANSLATE,
                            size=16,
                            color=self.theme.color_scheme.primary,
                        ),
                        ft.Text(
                            "Local Translation",
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color=self.theme.color_scheme.on_surface,
                        ),
                    ],
                    spacing=6,
                ),
                ft.Container(height=10),
                # 模型卡片列表
                ft.Column(
                    controls=model_cards,
                    spacing=4,
                ),
                ft.Container(height=6),
                # 提示文字
                ft.Text(
                    hint_text,
                    size=10,
                    color=self.theme.color_scheme.on_surface_variant,
                    italic=not any_available,
                ),
            ],
            spacing=0,
        )

    def _build_llm_section(self) -> ft.Control:
        """构建 LLM 状态部分 - 列表显示所有预设的连通性"""
        from mediafactory.constants import BackendConfigMapping
        from mediafactory.config import get_config

        config = get_config()
        presets = BackendConfigMapping.BASE_URL_PRESETS

        # 构建 LLM 卡片列表
        self._llm_cards = []
        for preset_id, preset_info in presets.items():
            if preset_id == "custom":
                continue

            # 从配置中获取连通性状态
            preset_config = config.openai_compatible.get_preset_config(preset_id)
            is_available = preset_config.connection_available

            # 状态图标和颜色
            if is_available:
                status_icon = ft.Icons.CHECK_CIRCLE
                status_color = SEMANTIC_COLORS["success"]
            elif preset_config.api_key:
                status_icon = ft.Icons.RADIO_BUTTON_UNCHECKED
                status_color = self.theme.color_scheme.outline
            else:
                status_icon = ft.Icons.REMOVE_CIRCLE_OUTLINE
                status_color = self.theme.color_scheme.outline

            card = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Text(
                            preset_info["display_name"],
                            size=11,
                            weight=ft.FontWeight.W_500,
                            color=self.theme.color_scheme.on_surface,
                            expand=True,
                        ),
                        ft.Icon(status_icon, size=14, color=status_color),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                bgcolor=self.theme.color_scheme.surface_variant,
                border_radius=self.theme.radius_sm,
            )
            self._llm_cards.append(card)

        # 统计配置状态
        configured_count = sum(
            1
            for preset_id in presets
            if preset_id != "custom"
            and config.openai_compatible.get_preset_config(preset_id).api_key
        )

        # 底部提示
        hint_text = (
            f"{configured_count} configured"
            if configured_count > 0
            else "Go to Settings to configure"
        )

        return ft.Column(
            controls=[
                # 标题
                ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.CLOUD,
                            size=16,
                            color=self.theme.color_scheme.primary,
                        ),
                        ft.Text(
                            "Remote LLM",
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color=self.theme.color_scheme.on_surface,
                        ),
                    ],
                    spacing=6,
                ),
                ft.Container(height=10),
                # LLM 卡片列表
                ft.Column(
                    controls=self._llm_cards,
                    spacing=4,
                ),
                ft.Container(height=6),
                # 提示文字
                ft.Text(
                    hint_text,
                    size=10,
                    color=self.theme.color_scheme.on_surface_variant,
                    italic=configured_count == 0,
                ),
            ],
            spacing=0,
        )

    def _start_initial_llm_test(self) -> None:
        """启动初始 LLM 连通性测试（已移除，改为启动时在 app.py 统一处理）"""
        pass

    def update_statuses(
        self,
        whisper_status: Optional[ModelStatus] = None,
        translation_status: Optional[ModelStatus] = None,
        llm_status: Optional[ModelStatus] = None,
    ) -> None:
        """更新模型状态"""
        if whisper_status:
            self.whisper_status = whisper_status
        if translation_status:
            self.translation_status = translation_status
        if llm_status:
            self.llm_status = llm_status
