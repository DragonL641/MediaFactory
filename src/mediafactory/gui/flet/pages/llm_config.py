"""
Remote LLM Config 页面

卡片式多供应商管理界面，支持添加/编辑/删除/测试 LLM API 配置。
"""

from typing import Dict, Any, List
import flet as ft

from mediafactory.gui.flet.theme import get_theme, SEMANTIC_COLORS
from mediafactory.config import get_config, update_config
from mediafactory.logging import log_info, log_error
from mediafactory.constants import BackendConfigMapping


# API presets - use centralized definition from constants
API_PRESETS = {
    key: {"name": preset["display_name"], "base_url": preset["base_url"]}
    for key, preset in BackendConfigMapping.BASE_URL_PRESETS.items()
}


class LLMConfigPage:
    """Remote LLM Config 页面 - 卡片式多供应商管理"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.theme = get_theme()
        self.config = get_config()

        # 对话框引用
        self._dialog: ft.Control = None

        # 页面内容容器引用
        self._content_column: ft.Column = None

    def build(self) -> ft.Control:
        """构建页面"""
        self._content_column = ft.Column(
            controls=self._build_content_controls(),
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        return self._content_column

    def _build_content_controls(self) -> List[ft.Control]:
        """构建页面内容控件列表"""
        controls = [
            # 标题行
            ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.CLOUD_OUTLINED,
                        size=24,
                        color=self.theme.color_scheme.primary,
                    ),
                    ft.Text(
                        "Remote LLMs",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=self.theme.color_scheme.on_surface,
                    ),
                    ft.Container(expand=True),
                    ft.TextButton(
                        "Add Provider",
                        icon=ft.Icons.ADD,
                        on_click=self._on_add_provider,
                        style=ft.ButtonStyle(
                            color=self.theme.color_scheme.primary,
                        ),
                    ),
                ],
                spacing=12,
            ),
            ft.Divider(color=self.theme.color_scheme.outline_variant, height=1),
        ]

        # 获取所有已配置的预设
        configured_presets = self._get_configured_presets()

        if not configured_presets:
            # 空状态提示
            controls.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(
                                ft.Icons.CLOUD_OFF_OUTLINED,
                                size=48,
                                color=self.theme.color_scheme.on_surface_variant,
                            ),
                            ft.Text(
                                "No LLM providers configured",
                                size=14,
                                color=self.theme.color_scheme.on_surface_variant,
                            ),
                            ft.Text(
                                "Click 'Add Provider' to configure a remote LLM API",
                                size=12,
                                color=self.theme.color_scheme.on_surface_variant,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    padding=40,
                    alignment=ft.alignment.center,
                )
            )
        else:
            # 显示 LLM 卡片列表
            for preset_key, preset_config in configured_presets.items():
                controls.append(self._build_llm_card(preset_key, preset_config))

        return controls

    def _get_configured_presets(self) -> Dict[str, Any]:
        """获取所有已配置的预设"""
        presets = {}
        try:
            if hasattr(self.config, "openai_compatible"):
                for preset_key in API_PRESETS.keys():
                    preset_config = self.config.openai_compatible.get_preset_config(preset_key)
                    # 检查是否有实际配置（api_key 非空）
                    if preset_config.api_key:
                        presets[preset_key] = preset_config
        except Exception as e:
            log_error(f"获取配置失败: {e}")
        return presets

    def _build_llm_card(self, preset_key: str, preset_config) -> ft.Control:
        """构建单个 LLM 供应商卡片"""
        preset_info = API_PRESETS.get(preset_key, {})
        is_connected = getattr(preset_config, "connection_available", False)

        # 连接状态徽章
        status_badge = self._build_connection_badge(is_connected)

        return ft.Container(
            content=ft.Column(
                controls=[
                    # 第一行：名称 + 连接状态
                    ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.CLOUD_QUEUE,
                                size=18,
                                color=self.theme.color_scheme.primary,
                            ),
                            ft.Text(
                                preset_info.get("name", preset_key),
                                size=14,
                                weight=ft.FontWeight.W_500,
                                color=self.theme.color_scheme.on_surface,
                            ),
                            ft.Container(expand=True),
                            status_badge,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Container(height=8),
                    # 第二行：配置信息
                    ft.Text(
                        f"Base URL: {preset_config.base_url or 'Not configured'}",
                        size=11,
                        color=self.theme.color_scheme.on_surface_variant,
                    ),
                    ft.Text(
                        f"Model: {preset_config.model or 'Not configured'}",
                        size=11,
                        color=self.theme.color_scheme.on_surface_variant,
                    ),
                    ft.Container(height=8),
                    # 第三行：操作按钮
                    ft.Row(
                        controls=[
                            ft.TextButton(
                                "Test",
                                icon=ft.Icons.WIFI_FIND,
                                on_click=lambda e, pk=preset_key: self._on_test_connection(pk),
                                style=ft.ButtonStyle(
                                    color=self.theme.color_scheme.primary,
                                ),
                            ),
                            ft.TextButton(
                                "Edit",
                                icon=ft.Icons.EDIT_OUTLINED,
                                on_click=lambda e, pk=preset_key: self._on_edit_provider(pk),
                                style=ft.ButtonStyle(
                                    color=self.theme.color_scheme.on_surface_variant,
                                ),
                            ),
                            ft.TextButton(
                                "Delete",
                                icon=ft.Icons.DELETE_OUTLINED,
                                on_click=lambda e, pk=preset_key: self._on_delete_provider(pk),
                                style=ft.ButtonStyle(
                                    color=self.theme.color_scheme.error,
                                ),
                            ),
                        ],
                        spacing=0,
                    ),
                ],
                spacing=4,
            ),
            padding=16,
            bgcolor=self.theme.color_scheme.surface,
            border_radius=12,
            border=ft.border.all(1, self.theme.color_scheme.outline_variant),
        )

    def _build_connection_badge(self, is_connected: bool) -> ft.Control:
        """构建连接状态徽章"""
        if is_connected:
            return ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.CHECK_CIRCLE, size=14, color=SEMANTIC_COLORS["success"]),
                        ft.Text("Connected", size=11, color=SEMANTIC_COLORS["success"]),
                    ],
                    spacing=4,
                ),
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                bgcolor="#E8F5E9",  # 浅绿色背景
                border_radius=12,
            )
        else:
            return ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.CANCEL_OUTLINED, size=14, color=self.theme.color_scheme.on_surface_variant),
                        ft.Text("Not Connected", size=11, color=self.theme.color_scheme.on_surface_variant),
                    ],
                    spacing=4,
                ),
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                bgcolor=self.theme.color_scheme.surface_variant,
                border_radius=12,
            )

    def _on_add_provider(self, e) -> None:
        """添加新供应商"""
        self._show_provider_dialog(None)

    def _on_edit_provider(self, preset_key: str) -> None:
        """编辑供应商"""
        self._show_provider_dialog(preset_key)

    def _on_delete_provider(self, preset_key: str) -> None:
        """删除供应商"""
        # log_info(f"Delete provider button clicked: {preset_key}")
        def on_confirm(e):
            self._delete_provider_config(preset_key)
            self._close_dialog()
            self._refresh_page()

        def on_cancel(e):
            self._close_dialog()

        self._dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Delete Provider"),
            content=ft.Text(f"Are you sure you want to delete {API_PRESETS.get(preset_key, {}).get('name', preset_key)}?"),
            actions=[
                ft.TextButton("Cancel", on_click=on_cancel),
                ft.TextButton("Delete", on_click=on_confirm, style=ft.ButtonStyle(color=self.theme.color_scheme.error)),
            ],
        )
        self.page.show_dialog(self._dialog)

    def _delete_provider_config(self, preset_key: str) -> None:
        """删除供应商配置"""
        try:
            update_config(
                **{
                    f"openai_compatible__{preset_key}__api_key": "",
                    f"openai_compatible__{preset_key}__connection_available": False,
                }
            )
            log_info(f"已删除供应商配置: {preset_key}")
            self._show_snackbar("Provider deleted", SEMANTIC_COLORS["success"])
        except Exception as ex:
            log_error(f"删除配置失败: {ex}")
            self._show_snackbar(f"Delete failed: {str(ex)[:50]}", self.theme.color_scheme.error)

    def _show_provider_dialog(self, preset_key: str = None) -> None:
        """显示供应商配置对话框"""
        # log_info(f"_show_provider_dialog called with preset_key={preset_key}")
        is_edit = preset_key is not None

        # 加载现有配置（如果是编辑模式）
        if is_edit:
            preset_config = self.config.openai_compatible.get_preset_config(preset_key)
            current_base_url = preset_config.base_url or API_PRESETS.get(preset_key, {}).get("base_url", "")
            current_api_key = preset_config.api_key or ""
            current_model = preset_config.model or ""
            current_max_tokens = getattr(preset_config, "max_tokens", 0)
        else:
            preset_key = "openai"
            current_base_url = API_PRESETS.get("openai", {}).get("base_url", "")
            current_api_key = ""
            current_model = ""
            current_max_tokens = 0

        # 表单控件
        preset_dropdown = ft.Dropdown(
            label="Provider",
            options=[ft.dropdown.Option(k, v["name"]) for k, v in API_PRESETS.items()],
            value=preset_key,
            disabled=is_edit,  # 编辑模式不允许更改预设
            dense=True,
            border_color=self.theme.color_scheme.outline_variant,
            text_style=ft.TextStyle(color=self.theme.color_scheme.on_surface, size=12),
            label_style=ft.TextStyle(color=self.theme.color_scheme.on_surface_variant, size=11),
            content_padding=ft.padding.symmetric(horizontal=12, vertical=8),
        )

        base_url_field = ft.TextField(
            label="Base URL",
            value=current_base_url,
            dense=True,
            border_color=self.theme.color_scheme.outline_variant,
            text_style=ft.TextStyle(color=self.theme.color_scheme.on_surface, size=12),
            label_style=ft.TextStyle(color=self.theme.color_scheme.on_surface_variant, size=11),
        )

        api_key_field = ft.TextField(
            label="API Key",
            value=current_api_key,
            password=True,
            can_reveal_password=True,
            dense=True,
            border_color=self.theme.color_scheme.outline_variant,
            text_style=ft.TextStyle(color=self.theme.color_scheme.on_surface, size=12),
            label_style=ft.TextStyle(color=self.theme.color_scheme.on_surface_variant, size=11),
        )

        model_field = ft.TextField(
            label="Model",
            value=current_model,
            hint_text="e.g., gpt-4o-mini, deepseek-chat",
            dense=True,
            border_color=self.theme.color_scheme.outline_variant,
            text_style=ft.TextStyle(color=self.theme.color_scheme.on_surface, size=12),
            label_style=ft.TextStyle(color=self.theme.color_scheme.on_surface_variant, size=11),
        )

        max_tokens_field = ft.TextField(
            label="Max Tokens",
            value=str(current_max_tokens) if current_max_tokens > 0 else "",
            hint_text="0 = use model default",
            dense=True,
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=self.theme.color_scheme.outline_variant,
            text_style=ft.TextStyle(color=self.theme.color_scheme.on_surface, size=12),
            label_style=ft.TextStyle(color=self.theme.color_scheme.on_surface_variant, size=11),
        )

        status_text = ft.Text("", size=11)

        def on_preset_change(e):
            selected = e.control.value
            if selected in API_PRESETS:
                base_url_field.value = API_PRESETS[selected]["base_url"]
                base_url_field.update()

        def on_save(e):
            preset = preset_dropdown.value
            base_url = base_url_field.value.strip()
            api_key = api_key_field.value.strip()
            model = model_field.value.strip()
            max_tokens_str = max_tokens_field.value.strip()

            if not api_key:
                status_text.value = "API Key is required"
                status_text.color = self.theme.color_scheme.error
                status_text.update()
                return

            try:
                max_tokens = int(max_tokens_str) if max_tokens_str else 0
            except ValueError:
                max_tokens = 0

            try:
                update_config(
                    **{
                        f"openai_compatible__{preset}__base_url": base_url,
                        f"openai_compatible__{preset}__api_key": api_key,
                        f"openai_compatible__{preset}__model": model,
                        f"openai_compatible__{preset}__max_tokens": max_tokens,
                    }
                )
                log_info(f"配置已保存: {preset}")
                self._close_dialog()
                self._refresh_page()
                self._show_snackbar("Configuration saved", SEMANTIC_COLORS["success"])
            except Exception as ex:
                status_text.value = f"Save failed: {str(ex)[:50]}"
                status_text.color = self.theme.color_scheme.error
                status_text.update()

        def on_cancel(e):
            self._close_dialog()

        preset_dropdown.on_select = on_preset_change

        # log_info("Creating dialog...")
        self._dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Edit Provider" if is_edit else "Add Provider"),
            content=ft.Column(
                controls=[
                    preset_dropdown,
                    base_url_field,
                    api_key_field,
                    model_field,
                    max_tokens_field,
                    status_text,
                ],
                spacing=12,
                tight=True,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=on_cancel),
                ft.TextButton("Save", on_click=on_save, style=ft.ButtonStyle(color=SEMANTIC_COLORS["success"])),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(self._dialog)

    def _on_test_connection(self, preset_key: str) -> None:
        """测试连接"""
        import threading

        preset_config = self.config.openai_compatible.get_preset_config(preset_key)
        base_url = preset_config.base_url
        api_key = preset_config.api_key
        model = preset_config.model or "gpt-4o-mini"

        if not base_url or not api_key:
            self._show_snackbar("Please configure Base URL and API Key first", self.theme.color_scheme.error)
            return

        self._show_snackbar("Testing connection...", self.theme.color_scheme.primary)

        def run_test():
            try:
                from mediafactory.llm import OpenAICompatibleBackend

                backend = OpenAICompatibleBackend(
                    base_url=base_url,
                    api_key=api_key,
                    model=model,
                )

                result = backend.test_connection()

                if result["success"]:
                    update_config(
                        **{f"openai_compatible__{preset_key}__connection_available": True}
                    )
                    self._show_snackbar(f"Connection successful: {result['message']}", SEMANTIC_COLORS["success"])
                else:
                    update_config(
                        **{f"openai_compatible__{preset_key}__connection_available": False}
                    )
                    self._show_snackbar(f"Connection failed: {result['message']}", self.theme.color_scheme.error)

            except Exception as ex:
                update_config(
                    **{f"openai_compatible__{preset_key}__connection_available": False}
                )
                self._show_snackbar(f"Test failed: {str(ex)[:50]}", self.theme.color_scheme.error)

            self._refresh_page()

        thread = threading.Thread(target=run_test, daemon=True)
        thread.start()

    def _close_dialog(self) -> None:
        """关闭对话框"""
        if self._dialog:
            self.page.pop_dialog()
            self._dialog = None

    def _refresh_page(self) -> None:
        """刷新页面"""
        self.config = get_config()
        if self._content_column is not None:
            self._content_column.controls = self._build_content_controls()
            self._content_column.update()

    def _show_snackbar(self, message: str, color: str) -> None:
        """显示消息横幅"""
        try:
            snackbar = ft.SnackBar(
                content=ft.Text(message, color=color),
                duration=3000,
            )
            self.page.overlay.append(snackbar)
            snackbar.open = True
            self.page.update()
        except Exception:
            pass


def build_llm_config_page(page: ft.Page, params: Dict[str, Any]) -> ft.Control:
    """构建 LLM Config 页面"""
    llm_config_page = LLMConfigPage(page)
    return llm_config_page.build()
