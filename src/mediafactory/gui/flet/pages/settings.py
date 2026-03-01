"""
设置页面

包含本地翻译模型管理和 LLM API 配置。
"""

from typing import Dict, Any, List
import flet as ft

from mediafactory.gui.flet.theme import get_theme, SEMANTIC_COLORS
from mediafactory.gui.flet.state import get_state
from mediafactory.config import get_config
from mediafactory.logging import log_info, log_error
from mediafactory.constants import BackendConfigMapping

# API presets - use centralized definition from constants
API_PRESETS = {
    key: {"name": preset["display_name"], "base_url": preset["base_url"]}
    for key, preset in BackendConfigMapping.BASE_URL_PRESETS.items()
}

# 本地翻译模型列表（使用 huggingface_id）
LOCAL_TRANSLATION_MODELS = [
    {
        "id": "google/madlad400-3b-mt",
        "name": "MADLAD400-3B Q4K",
        "params": "3B",
        "precision": "Q4K",
        "runtime_memory": "3-4 GB",
    },
    {
        "id": "google/madlad400-7b-mt-bt",
        "name": "MADLAD400-7B Q4K",
        "params": "7B",
        "precision": "Q4K",
        "runtime_memory": "6-7 GB",
    },
    {
        "id": "google/madlad400-3b-mt-fp16",
        "name": "MADLAD400-3B FP16",
        "params": "3B",
        "precision": "FP16",
        "runtime_memory": "9-10 GB",
    },
]

# 本地音频处理模型
LOCAL_AUDIO_MODELS = [
    {
        "id": "Systran/faster-whisper-large-v3",
        "name": "Faster Whisper Large V3",
        "params": "1.5B",
        "precision": "FP16/INT8",
        "runtime_memory": "4-5 GB",
    },
]


class SettingsPage:
    """设置页面"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.theme = get_theme()
        self.state = get_state()
        self.config = get_config()

        # 状态
        self._api_preset = "openai"
        self._api_base_url = ""
        self._api_key = ""
        self._api_model = ""
        self._api_max_tokens = 0  # 0 表示使用模型默认限制

        # 模型下载状态跟踪 {model_id: {"status": "downloading" | "deleting", "progress": 0-100, "message": str}}
        self._model_download_states: Dict[str, Dict] = {}

        # 页面内容容器引用（用于动态刷新）
        self._content_column: ft.Column = None

    def build(self) -> ft.Control:
        """构建页面"""
        # 加载配置
        self._load_config()

        # 存储内容列引用以便后续刷新
        self._content_column = ft.Column(
            controls=self._build_content_controls(),
            spacing=15,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        return self._content_column

    def _build_content_controls(self) -> List[ft.Control]:
        """构建页面内容控件列表"""
        return [
            # 标题
            ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.SETTINGS,
                        size=32,
                        color=self.theme.color_scheme.primary,
                    ),
                    ft.Text(
                        "Settings",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color=self.theme.color_scheme.on_surface,
                    ),
                ],
                spacing=15,
            ),
            ft.Divider(color=self.theme.color_scheme.outline_variant),
            # === 本地音频处理模型管理区域 ===
            self._build_audio_models_section(),
            ft.Container(height=20),
            # === 本地翻译模型管理区域 ===
            self._build_translation_models_section(),
            ft.Container(height=20),
            # === LLM API 配置区域 ===
            self._build_llm_api_section(),
            ft.Container(height=20),
            # === 关于区域 ===
            self._build_about_section(),
        ]

    def _build_audio_models_section(self) -> ft.Control:
        """构建本地音频处理模型管理区域"""
        # 模型表格
        model_rows = [self._build_table_header()]
        for model in LOCAL_AUDIO_MODELS:
            model_rows.append(self._build_model_row(model))

        return ft.Container(
            content=ft.Column(
                controls=[
                    # 标题
                    ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.MIC,
                                color=self.theme.color_scheme.primary,
                                size=18,
                            ),
                            ft.Text(
                                "Local Audio Processing Model Management",
                                size=14,
                                weight=ft.FontWeight.W_500,
                                color=self.theme.color_scheme.on_surface,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Container(height=12),
                    # 模型表格
                    ft.Column(
                        controls=model_rows,
                        spacing=6,
                    ),
                ],
                spacing=0,
            ),
            padding=12,
            bgcolor=self.theme.color_scheme.surface,
            border_radius=8,
            border=ft.border.all(1, self.theme.color_scheme.outline_variant),
        )

    def _build_translation_models_section(self) -> ft.Control:
        """构建本地翻译模型管理区域"""
        # 模型表格
        model_rows = [self._build_table_header()]
        for model in LOCAL_TRANSLATION_MODELS:
            model_rows.append(self._build_model_row(model))

        return ft.Container(
            content=ft.Column(
                controls=[
                    # 标题
                    ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.TRANSLATE,
                                color=self.theme.color_scheme.primary,
                                size=18,
                            ),
                            ft.Text(
                                "Local Translation Model Management",
                                size=14,
                                weight=ft.FontWeight.W_500,
                                color=self.theme.color_scheme.on_surface,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Container(height=12),
                    # 模型表格
                    ft.Column(
                        controls=model_rows,
                        spacing=6,
                    ),
                ],
                spacing=0,
            ),
            padding=12,
            bgcolor=self.theme.color_scheme.surface,
            border_radius=8,
            border=ft.border.all(1, self.theme.color_scheme.outline_variant),
        )

    def _build_table_header(self) -> ft.Control:
        """构建表格头部"""
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Text(
                            "Model",
                            size=12,
                            weight=ft.FontWeight.W_600,
                            color=self.theme.color_scheme.on_surface_variant,
                        ),
                        expand=4,
                        alignment=ft.Alignment(-1, 0),  # center_left
                    ),
                    ft.Container(
                        content=ft.Text(
                            "Params",
                            size=12,
                            weight=ft.FontWeight.W_600,
                            color=self.theme.color_scheme.on_surface_variant,
                        ),
                        expand=2,
                        alignment=ft.Alignment(0, 0),  # center
                    ),
                    ft.Container(
                        content=ft.Text(
                            "Precision",
                            size=12,
                            weight=ft.FontWeight.W_600,
                            color=self.theme.color_scheme.on_surface_variant,
                        ),
                        expand=2,
                        alignment=ft.Alignment(0, 0),  # center
                    ),
                    ft.Container(
                        content=ft.Text(
                            "Runtime Mem",
                            size=12,
                            weight=ft.FontWeight.W_600,
                            color=self.theme.color_scheme.on_surface_variant,
                        ),
                        expand=2,
                        alignment=ft.Alignment(0, 0),  # center
                    ),
                    ft.Container(
                        content=ft.Text(
                            "Status",
                            size=12,
                            weight=ft.FontWeight.W_600,
                            color=self.theme.color_scheme.on_surface_variant,
                        ),
                        expand=1,
                        alignment=ft.Alignment(0, 0),  # center
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.only(bottom=10, left=4, right=4),
            border=ft.border.only(
                bottom=ft.BorderSide(1, self.theme.color_scheme.outline_variant)
            ),
        )

    def _build_model_row(self, model: Dict[str, str]) -> ft.Control:
        """构建模型行"""
        model_id = model["id"]
        downloaded = self._check_model_downloaded(model_id)
        download_state = self._model_download_states.get(model_id)

        # 根据状态构建不同的控件
        if download_state and download_state.get("status") == "downloading":
            # 下载中：显示进度条和详细信息
            progress = download_state.get("progress", 0)
            message = download_state.get("message", "Downloading...")

            status_control = ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.ProgressBar(
                                width=80,
                                height=4,
                                value=progress / 100 if progress > 0 else None,
                                color=self.theme.color_scheme.primary,
                                bgcolor=self.theme.color_scheme.surface_variant,
                            ),
                            ft.Text(
                                f"{progress}%",
                                size=10,
                                color=self.theme.color_scheme.primary,
                                weight=ft.FontWeight.W_500,
                            ),
                        ],
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Text(
                        message,
                        size=9,
                        color=self.theme.color_scheme.on_surface_variant,
                        no_wrap=True,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                ],
                spacing=2,
                horizontal_alignment=ft.CrossAxisAlignment.END,
            )
        elif downloaded:
            # 已下载：显示删除按钮
            status_control = ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                icon_color=self.theme.color_scheme.error,
                icon_size=20,
                tooltip="Delete model",
                data=model_id,
                on_click=self._on_delete_click_wrapper,
            )
        else:
            # 未下载：显示下载按钮
            status_control = ft.IconButton(
                icon=ft.Icons.DOWNLOAD_ROUNDED,
                icon_color=self.theme.color_scheme.primary,
                icon_size=20,
                tooltip="Download model",
                data=model_id,
                on_click=self._on_download_click_wrapper,
            )

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Text(
                            model["name"],
                            size=13,
                            color=self.theme.color_scheme.on_surface,
                            no_wrap=True,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        expand=4,
                        alignment=ft.Alignment(-1, 0),
                    ),
                    ft.Container(
                        content=ft.Text(
                            model["params"],
                            size=13,
                            color=self.theme.color_scheme.on_surface_variant,
                        ),
                        expand=2,
                        alignment=ft.Alignment(0, 0),
                    ),
                    ft.Container(
                        content=ft.Text(
                            model["precision"],
                            size=13,
                            color=self.theme.color_scheme.on_surface_variant,
                        ),
                        expand=2,
                        alignment=ft.Alignment(0, 0),
                    ),
                    ft.Container(
                        content=ft.Text(
                            model["runtime_memory"],
                            size=13,
                            color=self.theme.color_scheme.on_surface_variant,
                        ),
                        expand=2,
                        alignment=ft.Alignment(0, 0),
                    ),
                    status_control,
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(vertical=8, horizontal=4),
        )

    def _check_model_downloaded(self, model_id: str) -> bool:
        """检查模型是否已下载"""
        try:
            from mediafactory.models.local_models import local_model_manager

            return local_model_manager.is_model_available_locally(model_id)
        except Exception:
            return False

    def _build_llm_api_section(self) -> ft.Control:
        """构建 LLM API 配置区域"""
        # API 预设选择
        self._preset_dropdown = ft.Dropdown(
            label="API Preset",
            options=[ft.dropdown.Option(k, v["name"]) for k, v in API_PRESETS.items()],
            value=self._api_preset,
            dense=True,
            on_select=self._on_preset_change,
            border_color=self.theme.color_scheme.outline_variant,
            text_style=ft.TextStyle(color=self.theme.color_scheme.on_surface, size=12),
            label_style=ft.TextStyle(
                color=self.theme.color_scheme.on_surface_variant, size=11
            ),
            content_padding=ft.padding.symmetric(horizontal=12, vertical=8),
        )

        # Base URL
        self._base_url_field = ft.TextField(
            label="Base URL",
            value=self._api_base_url,
            hint_text="API base URL",
            dense=True,
            border_color=self.theme.color_scheme.outline_variant,
            text_style=ft.TextStyle(color=self.theme.color_scheme.on_surface, size=12),
            label_style=ft.TextStyle(
                color=self.theme.color_scheme.on_surface_variant, size=11
            ),
        )

        # API Key
        self._api_key_field = ft.TextField(
            label="API Key",
            value=self._api_key,
            hint_text="Enter your API key",
            password=True,
            can_reveal_password=True,
            dense=True,
            border_color=self.theme.color_scheme.outline_variant,
            text_style=ft.TextStyle(color=self.theme.color_scheme.on_surface, size=12),
            label_style=ft.TextStyle(
                color=self.theme.color_scheme.on_surface_variant, size=11
            ),
        )

        # Model
        self._model_field = ft.TextField(
            label="Model",
            value=self._api_model,
            hint_text="e.g., gpt-4o-mini, deepseek-chat",
            dense=True,
            border_color=self.theme.color_scheme.outline_variant,
            text_style=ft.TextStyle(color=self.theme.color_scheme.on_surface, size=12),
            label_style=ft.TextStyle(
                color=self.theme.color_scheme.on_surface_variant, size=11
            ),
            on_change=self._on_model_change,
        )

        # Max Tokens
        self._max_tokens_field = ft.TextField(
            label="Max Tokens",
            value=str(self._api_max_tokens) if self._api_max_tokens > 0 else "",
            hint_text="0 = use model default",
            dense=True,
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=self.theme.color_scheme.outline_variant,
            text_style=ft.TextStyle(color=self.theme.color_scheme.on_surface, size=12),
            label_style=ft.TextStyle(
                color=self.theme.color_scheme.on_surface_variant, size=11
            ),
        )

        # 测试状态
        self._test_status = ft.Text("", size=11)

        return ft.Container(
            content=ft.Column(
                controls=[
                    # 标题
                    ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.CLOUD_OUTLINED,
                                color=self.theme.color_scheme.primary,
                                size=18,
                            ),
                            ft.Text(
                                "LLM API Configuration",
                                size=14,
                                weight=ft.FontWeight.W_500,
                                color=self.theme.color_scheme.on_surface,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Container(height=8),
                    ft.Text(
                        "Configure remote LLM API for text translation. If not configured, local models will be used.",
                        size=11,
                        color=self.theme.color_scheme.on_surface_variant,
                    ),
                    ft.Container(height=12),
                    self._preset_dropdown,
                    self._base_url_field,
                    self._api_key_field,
                    self._model_field,
                    self._max_tokens_field,
                    ft.Container(height=8),
                    ft.Row(
                        controls=[
                            ft.TextButton(
                                "Test Connection",
                                icon=ft.Icons.WIFI_FIND,
                                on_click=self._on_test_connection,
                                style=ft.ButtonStyle(
                                    color=self.theme.color_scheme.primary,
                                ),
                            ),
                            ft.TextButton(
                                "Save",
                                icon=ft.Icons.SAVE,
                                on_click=self._on_save,
                                style=ft.ButtonStyle(
                                    color=SEMANTIC_COLORS["success"],
                                ),
                            ),
                        ],
                        spacing=8,
                    ),
                    self._test_status,
                ],
                spacing=6,
            ),
            padding=12,
            bgcolor=self.theme.color_scheme.surface,
            border_radius=8,
            border=ft.border.all(1, self.theme.color_scheme.outline_variant),
        )

    def _build_about_section(self) -> ft.Control:
        """构建关于区域"""
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.INFO_OUTLINE,
                                color=self.theme.color_scheme.primary,
                                size=18,
                            ),
                            ft.Text(
                                "About",
                                size=14,
                                weight=ft.FontWeight.W_500,
                                color=self.theme.color_scheme.on_surface,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Container(height=8),
                    ft.Text(
                        "MediaFactory - Multimedia Processing Platform\n"
                        "Version: 3.2.0",
                        size=11,
                        color=self.theme.color_scheme.on_surface_variant,
                    ),
                ],
                spacing=0,
            ),
            padding=12,
            bgcolor=self.theme.color_scheme.surface,
            border_radius=8,
            border=ft.border.all(1, self.theme.color_scheme.outline_variant),
        )

    def _load_config(self) -> None:
        """加载配置"""
        try:
            if hasattr(self.config, "openai_compatible"):
                api_config = self.config.openai_compatible
                preset_name = api_config.current_preset

                # 获取当前预设的配置
                preset_config = api_config.get_preset_config(preset_name)
                self._api_preset = preset_name
                self._api_base_url = preset_config.base_url
                self._api_key = preset_config.api_key
                self._api_model = preset_config.model
                self._api_max_tokens = getattr(preset_config, "max_tokens", 0)
        except Exception:
            pass

    def _on_model_change(self, e) -> None:
        """模型变更"""
        pass  # 目前不需要处理

    def _on_preset_change(self, e) -> None:
        """预设变更"""
        self._api_preset = e.control.value

        # 从 API_PRESETS 获取默认 base_url
        if self._api_preset in API_PRESETS:
            self._base_url_field.value = API_PRESETS[self._api_preset]["base_url"]

        # 从 config 获取已保存的值
        if hasattr(self.config, "openai_compatible"):
            preset_config = self.config.openai_compatible.get_preset_config(
                self._api_preset
            )
            if preset_config.base_url:
                self._base_url_field.value = preset_config.base_url
            self._api_key_field.value = preset_config.api_key or ""
            self._model_field.value = preset_config.model or ""
            max_tokens = getattr(preset_config, "max_tokens", 0)
            self._max_tokens_field.value = str(max_tokens) if max_tokens > 0 else ""
            self._api_max_tokens = max_tokens

        # 更新 UI
        self._base_url_field.update()
        self._api_key_field.update()
        self._model_field.update()
        self._max_tokens_field.update()

    def _on_test_connection(self, e) -> None:
        """测试连接

        Note: 这里直接创建 OpenAICompatibleBackend 而不是使用 initialize_llm_backend()，
        因为用户可能正在编辑配置（值还没保存到 config），我们需要用 UI 中的当前值来测试。
        """
        from mediafactory.llm import OpenAICompatibleBackend
        from mediafactory.config import update_config
        import threading

        base_url = self._base_url_field.value.strip()
        api_key = self._api_key_field.value.strip()
        model = self._model_field.value.strip()

        if not base_url or not api_key:
            self._test_status.value = "Please enter Base URL and API Key"
            self._test_status.color = self.theme.color_scheme.error
            self._test_status.update()
            return

        self._test_status.value = "Testing..."
        self._test_status.color = self.theme.color_scheme.primary
        self._test_status.update()

        # Store references for use in thread
        success_color = SEMANTIC_COLORS["success"]
        error_color = self.theme.color_scheme.error
        current_preset = self._api_preset

        def run_test():
            """在后台线程中运行测试（使用同步的 test_connection 方法）"""
            try:
                # 直接创建 backend，使用 UI 中用户输入的值（可能还没保存到配置）
                backend = OpenAICompatibleBackend(
                    base_url=base_url,
                    api_key=api_key,
                    model=model or "gpt-4o-mini",
                )

                # 使用 test_connection() 方法（同步，返回 dict）
                result = backend.test_connection()

                if result["success"]:
                    self._test_status.value = f"✓ {result['message']}"
                    self._test_status.color = success_color
                    try:
                        update_config(
                            **{
                                f"openai_compatible__{current_preset}__connection_available": True
                            }
                        )
                    except Exception as ex:
                        log_info(f"Failed to save connection status: {ex}")
                else:
                    self._test_status.value = f"✗ {result['message']}"
                    self._test_status.color = error_color
                    try:
                        update_config(
                            **{
                                f"openai_compatible__{current_preset}__connection_available": False
                            }
                        )
                    except Exception as ex:
                        log_info(f"Failed to save connection status: {ex}")

            except Exception as ex:
                self._test_status.value = f"Error: {str(ex)[:50]}"
                self._test_status.color = error_color
                try:
                    update_config(
                        **{
                            f"openai_compatible__{current_preset}__connection_available": False
                        }
                    )
                except Exception:
                    pass

            try:
                self._test_status.update()
            except Exception:
                pass

        thread = threading.Thread(target=run_test, daemon=True)
        thread.start()

    def _on_save(self, e) -> None:
        """保存配置"""
        from mediafactory.config import get_config_manager

        preset = self._api_preset
        base_url = self._base_url_field.value.strip()
        api_key = self._api_key_field.value.strip()
        model = self._model_field.value.strip()

        # 解析 max_tokens（空字符串或 0 表示使用模型默认）
        max_tokens_str = self._max_tokens_field.value.strip()
        try:
            max_tokens = int(max_tokens_str) if max_tokens_str else 0
        except ValueError:
            max_tokens = 0

        try:
            manager = get_config_manager()

            # 使用双下划线表示法更新配置
            manager.update(
                **{
                    f"openai_compatible__current_preset": preset,
                    f"openai_compatible__{preset}__base_url": base_url,
                    f"openai_compatible__{preset}__api_key": api_key,
                    f"openai_compatible__{preset}__model": model,
                    f"openai_compatible__{preset}__max_tokens": max_tokens,
                }
            )

            log_info("Settings saved")
            self._test_status.value = "Settings saved!"
            self._test_status.color = SEMANTIC_COLORS["success"]
        except Exception as ex:
            log_info(f"Failed to save settings: {ex}")
            self._test_status.value = f"Save failed: {str(ex)[:50]}"
            self._test_status.color = self.theme.color_scheme.error

        self._test_status.update()

    # ==================== 模型下载相关方法 ====================

    def _on_download_click_wrapper(self, e) -> None:
        """处理下载按钮点击事件的包装器"""
        model_id = e.control.data
        log_info(f"Download button clicked for model: {model_id}")
        self._start_download(model_id)

    def _on_delete_click_wrapper(self, e) -> None:
        """处理删除按钮点击事件的包装器"""
        model_id = e.control.data
        log_info(f"Delete button clicked for model: {model_id}")
        self._delete_model(model_id)

    def _start_download(self, model_id: str) -> None:
        """直接开始下载（无确认对话框）"""
        log_info(f"Starting download for: {model_id}")

        # 设置下载状态（包含进度信息）
        self._model_download_states[model_id] = {
            "status": "downloading",
            "progress": 0,
            "message": "Starting download...",
        }

        # 刷新 UI 显示进度条
        self._refresh_page()

        # 从 config.toml 读取下载源
        download_source = self._get_download_source()
        log_info(f"Using download source: {download_source}")

        # 开始后台下载
        self._download_in_background(model_id, download_source)

    def _get_download_source(self) -> str:
        """从配置读取下载源"""
        try:
            if hasattr(self.config, "model") and hasattr(
                self.config.model, "download_source"
            ):
                return self.config.model.download_source
        except Exception:
            pass
        # 默认使用 HuggingFace 镜像
        return "https://hf-mirror.com"

    def _delete_model(self, model_id: str) -> None:
        """删除已下载的模型"""
        log_info(f"Deleting model: {model_id}")

        # 设置删除状态
        self._model_download_states[model_id] = {
            "status": "deleting",
            "progress": 0,
            "message": "Deleting...",
        }
        self._refresh_page()

        # 存储颜色引用用于线程
        success_color = SEMANTIC_COLORS["success"]
        error_color = self.theme.color_scheme.error
        model_info = self._get_model_info(model_id)
        model_name = model_info["name"] if model_info else model_id

        def run_delete():
            try:
                from mediafactory.models.model_download import delete_model

                success, error_msg = delete_model(model_id)

                if success:
                    log_info(f"Model deleted: {model_id}")
                    self._show_snackbar(
                        f"Model '{model_name}' deleted successfully!", success_color
                    )
                else:
                    log_error(f"Failed to delete model: {model_id} - {error_msg}")
                    self._show_snackbar(
                        f"Failed to delete model '{model_name}': {error_msg[:50]}",
                        error_color,
                    )

            except Exception as ex:
                error_msg = str(ex)[:100]
                log_error(f"Delete failed: {error_msg}")
                self._show_snackbar(f"Delete failed: {error_msg}", error_color)

            finally:
                # 清除状态并刷新
                self._model_download_states.pop(model_id, None)
                self._refresh_model_status()
                self._refresh_page()

        import threading

        thread = threading.Thread(target=run_delete, daemon=True)
        thread.start()

    def _download_in_background(self, model_id: str, source: str) -> None:
        """在后台线程执行下载，使用轮询机制更新进度"""
        import threading
        from pathlib import Path

        # 存储颜色引用用于线程
        success_color = SEMANTIC_COLORS["success"]
        error_color = self.theme.color_scheme.error
        model_info = self._get_model_info(model_id)
        model_name = model_info["name"] if model_info else model_id

        # 获取模型总大小（用于计算进度）
        endpoint = None if source == "https://huggingface.co" else source
        total_size: list = [None]  # 使用列表以便在线程间共享
        download_completed: list = [False]  # 下载完成标志
        poll_stop: list = [False]  # 轮询停止标志

        def format_size(size_bytes: int) -> str:
            """格式化文件大小"""
            if size_bytes < 1024:
                return f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.1f} KB"
            elif size_bytes < 1024 * 1024 * 1024:
                return f"{size_bytes / (1024 * 1024):.1f} MB"
            else:
                return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

        def fetch_total_size():
            """获取模型总大小"""
            try:
                from mediafactory.models.model_download import get_model_total_size

                total_size[0] = get_model_total_size(model_id, endpoint)
                if total_size[0]:
                    log_info(
                        f"Model {model_id} total size: {format_size(total_size[0])}"
                    )
            except Exception as e:
                log_info(f"Failed to get model total size: {e}")

        def poll_progress():
            """轮询下载进度（每5秒）"""
            from mediafactory.models.model_download import (
                get_downloaded_size,
                get_models_dir,
            )

            # 先获取总大小
            fetch_total_size()

            while not poll_stop[0] and not download_completed[0]:
                try:
                    model_path = get_models_dir() / model_id
                    downloaded = get_downloaded_size(model_path)

                    if total_size[0] and total_size[0] > 0:
                        percent = min(100, int(downloaded / total_size[0] * 100))
                        message = f"{percent}% ({format_size(downloaded)} / {format_size(total_size[0])})"
                    else:
                        percent = 0
                        message = f"Downloading... ({format_size(downloaded)})"

                    self._model_download_states[model_id] = {
                        "status": "downloading",
                        "progress": percent,
                        "message": message,
                        "downloaded_size": downloaded,
                        "total_size": total_size[0],
                    }

                    try:
                        self._refresh_page()
                    except Exception:
                        pass

                except Exception as e:
                    log_info(f"Poll progress error: {e}")

                # 等待5秒
                for _ in range(50):
                    if poll_stop[0] or download_completed[0]:
                        break
                    import time

                    time.sleep(0.1)

        def run_download():
            """执行下载"""
            try:
                from mediafactory.models.model_download import (
                    download_model,
                    is_model_complete,
                )

                # 执行下载（不再使用进度回调）
                download_model(
                    huggingface_id=model_id,
                    download_source=source,
                )

                # 标记下载完成
                download_completed[0] = True

                # 验证模型完整性
                if is_model_complete(model_id):
                    log_info(f"Download complete and verified: {model_id}")

                    # 刷新模型状态
                    self._refresh_model_status()

                    # 显示成功消息
                    self._show_snackbar(
                        f"Model '{model_name}' downloaded successfully!", success_color
                    )
                else:
                    log_info(f"Download complete but verification failed: {model_id}")
                    self._show_snackbar(
                        f"Model '{model_name}' downloaded but verification failed. Please retry.",
                        error_color,
                    )

            except Exception as ex:
                download_completed[0] = True
                poll_stop[0] = True
                error_msg = str(ex)[:100]
                log_info(f"Download failed: {error_msg}")

                # 显示错误消息
                self._show_snackbar(f"Download failed: {error_msg}", error_color)

            finally:
                # 停止轮询
                poll_stop[0] = True
                # 清除下载状态并刷新 UI
                self._model_download_states.pop(model_id, None)
                self._refresh_page()

        # 启动轮询线程
        poll_thread = threading.Thread(target=poll_progress, daemon=True)
        poll_thread.start()

        # 启动下载线程
        download_thread = threading.Thread(target=run_download, daemon=True)
        download_thread.start()

    def _refresh_model_status(self) -> None:
        """刷新模型状态并更新 UI"""
        try:
            from mediafactory.config import get_config_manager

            # 重新扫描模型
            config_manager = get_config_manager()
            config_manager.sync_models_on_startup()

            # 重新加载配置
            self.config = get_config()

            log_info("Model status refreshed")
        except Exception as ex:
            log_info(f"Failed to refresh model status: {ex}")

    def _refresh_page(self) -> None:
        """刷新整个页面以更新 UI 状态"""
        try:
            if self._content_column is not None:
                # 重新构建内容控件
                self._content_column.controls = self._build_content_controls()
                self._content_column.update()
        except Exception as ex:
            log_info(f"Failed to refresh page: {ex}")

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

    def _get_model_info(self, model_id: str) -> dict:
        """获取模型信息"""
        # 从本地模型列表中查找
        for model in LOCAL_AUDIO_MODELS + LOCAL_TRANSLATION_MODELS:
            if model["id"] == model_id:
                return model
        return None


def build_settings_page(page: ft.Page, params: Dict[str, Any]) -> ft.Control:
    """构建设置页面"""
    settings_page = SettingsPage(page)
    return settings_page.build()
