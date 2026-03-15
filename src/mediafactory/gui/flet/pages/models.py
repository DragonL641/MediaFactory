"""
Models 页面

本地模型管理中心，使用卡片网格布局展示音频处理、翻译、视频增强模型。
使用 DownloadManager 实现串行下载队列。
使用统一的 MODEL_REGISTRY 管理所有模型。
"""

from typing import Dict, Any, List, Optional
import flet as ft

from mediafactory.gui.flet.theme import get_theme, SEMANTIC_COLORS
from mediafactory.config import get_config
from mediafactory.logging import log_info, log_error
from mediafactory.gui.flet.download_manager import (
    DownloadManager,
    DownloadStatus,
    get_download_manager,
)
from mediafactory.models.model_registry import (
    MODEL_REGISTRY,
    ModelType,
    is_model_downloaded,
    is_model_complete,
    is_enhancement_model,
)


def _get_models_by_type():
    """从统一注册表获取所有模型，按类型分组"""
    models = {
        "whisper": [],
        "translation": [],
        "super_resolution": [],
        "denoise": [],
        "face_restore": [],
    }
    
    for model_id, info in MODEL_REGISTRY.items():
        model_data = {
            "id": model_id,
            "name": info.display_name,
            "size": f"{info.model_size_mb} MB" if info.model_size_mb < 1024 else f"{info.model_size_mb / 1024:.1f} GB",
            "runtime_memory": f"{info.runtime_memory_mb} MB" if info.runtime_memory_mb < 1024 else f"{info.runtime_memory_mb / 1024:.1f} GB",
            "description": info.description,
        }
        
        if info.model_type == ModelType.WHISPER:
            models["whisper"].append(model_data)
        elif info.model_type == ModelType.TRANSLATION:
            models["translation"].append(model_data)
        elif info.model_type == ModelType.SUPER_RESOLUTION:
            models["super_resolution"].append(model_data)
        elif info.model_type == ModelType.DENOISE:
            models["denoise"].append(model_data)
        elif info.model_type == ModelType.FACE_RESTORE:
            models["face_restore"].append(model_data)
    
    return models


class ModelsPage:
    """Models 页面 - 卡片式本地模型管理中心（使用 DownloadManager）"""

    # 卡片宽度
    CARD_WIDTH = 300
    # UI 更新轮询间隔（毫秒）
    UI_POLL_INTERVAL = 1000

    def __init__(self, page: ft.Page):
        self.page = page
        self.theme = get_theme()
        self.config = get_config()

        # 使用 DownloadManager 替代 _model_download_states
        self._download_manager = get_download_manager()

        # 页面内容容器引用（用于动态刷新）
        self._content_column: ft.Column = None

        # UI 轮询定时器
        self._poll_timer: Optional[ft.Page] = None
        self._registered_models: set = set()  # 已注册回调的模型

        # 对话框引用
        self._dialog: Optional[ft.AlertDialog] = None

        # 删除状态管理（用于显示删除中状态）
        self._deleting_models: Dict[str, bool] = {}

    def build(self) -> ft.Control:
        """构建页面"""
        self._content_column = ft.Column(
            controls=self._build_content_controls(),
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        # 注册 DownloadManager 回调
        self._download_manager.register_callback(self._on_download_state_changed)

        return self._content_column

    def _build_content_controls(self) -> List[ft.Control]:
        """构建页面内容控件列表（从统一注册表获取所有模型）"""
        models_by_type = _get_models_by_type()
        
        return [
            # 标题
            ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.DOWNLOAD_OUTLINED,
                        size=24,
                        color=self.theme.color_scheme.primary,
                    ),
                    ft.Text(
                        "Local Models",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=self.theme.color_scheme.on_surface,
                    ),
                ],
                spacing=12,
            ),
            ft.Divider(color=self.theme.color_scheme.outline_variant, height=1),
            # === Whisper 模型区域 ===
            self._build_model_section(
                "Audio Processing Models",
                "Whisper models for speech recognition and transcription.",
                models_by_type["whisper"],
                "audio",
                ft.Icons.MIC,
            ),
            ft.Container(height=8),
            # === 翻译模型区域 ===
            self._build_model_section(
                "Translation Models",
                "MADLAD400 models for local text translation.",
                models_by_type["translation"],
                "translation",
                ft.Icons.TRANSLATE,
            ),
            ft.Container(height=8),
            # === 超分辨率模型区域 ===
            self._build_model_section(
                "Super Resolution (Real-ESRGAN)",
                "AI-powered video upscaling models.",
                models_by_type["super_resolution"],
                "enhancement",
                ft.Icons.ZOOM_IN,
            ),
            ft.Container(height=8),
            # === 去噪模型区域 ===
            self._build_model_section(
                "Denoising (NAFNet)",
                "Video denoise models for old or noisy footage.",
                models_by_type["denoise"],
                "enhancement",
                ft.Icons.BLUR_ON,
            ),
            ft.Container(height=8),
            # === 人脸修复模型区域 ===
            self._build_model_section(
                "Face Restoration (CodeFormer)",
                "Face detection and restoration models.",
                models_by_type["face_restore"],
                "enhancement",
                ft.Icons.FACE,
            ),
        ]

    def _build_model_section(
        self,
        title: str,
        description: str,
        models: List[Dict],
        model_type: str,
        icon: str,
    ) -> ft.Control:
        """构建模型卡片区域"""
        # 构建卡片列表
        card_controls = []
        for model in models:
            card_controls.append(self._build_model_card(model, model_type))

        return ft.Container(
            content=ft.Column(
                controls=[
                    # 标题行
                    ft.Row(
                        controls=[
                            ft.Icon(icon, color=self.theme.color_scheme.primary, size=18),
                            ft.Text(
                                title,
                                size=14,
                                weight=ft.FontWeight.W_500,
                                color=self.theme.color_scheme.on_surface,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Container(height=4),
                    ft.Text(description, size=11, color=self.theme.color_scheme.on_surface_variant),
                    ft.Container(height=12),
                    # 卡片网格
                    ft.Row(
                        controls=card_controls,
                        wrap=True,
                        spacing=12,
                        run_spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                ],
                spacing=0,
            ),
            padding=16,
            bgcolor=self.theme.color_scheme.surface,
            border_radius=12,
            border=ft.border.all(1, self.theme.color_scheme.outline_variant),
        )

    def _build_model_card(self, model: Dict, model_type: str) -> ft.Control:
        """构建模型卡片"""
        model_id = model["id"]
        downloaded = self._check_model_downloaded(model_id, model_type)

        # 从 DownloadManager 获取状态
        download_status = self._download_manager.get_status(model_id)
        progress = self._download_manager.get_progress(model_id)
        message = self._download_manager.get_message(model_id)

        # 操作区域
        action_control = self._build_model_action(
            model, downloaded, download_status, progress, message, model_type
        )

        return ft.Container(
            content=ft.Column(
                controls=[
                    # 图标 + 名称
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.POWER_OUTLINED, size=18, color=self.theme.color_scheme.primary),
                            ft.Text(
                                model["name"],
                                size=13,
                                weight=ft.FontWeight.W_500,
                                color=self.theme.color_scheme.on_surface,
                                expand=True,
                                no_wrap=True,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                    ),
                    ft.Divider(height=8, color=self.theme.color_scheme.outline_variant),
                    # 规格信息
                    ft.Text(f"Size: {model['size']}", size=10, color=self.theme.color_scheme.on_surface_variant),
                    ft.Text(f"Memory Required: {model['runtime_memory']}", size=10, color=self.theme.color_scheme.on_surface_variant),
                    ft.Text(f"Info: {model['description']}", size=10, color=self.theme.color_scheme.on_surface_variant, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Container(height=8),
                    # 操作区域
                    action_control,
                ],
                spacing=4,
            ),
            width=self.CARD_WIDTH,
            padding=12,
            bgcolor=self.theme.color_scheme.surface_variant,
            border_radius=8,
            border=ft.border.all(1, self.theme.color_scheme.outline_variant),
        )

    def _build_model_action(
        self,
        model: Dict,
        downloaded: bool,
        download_status: DownloadStatus,
        progress: float,
        message: str,
        model_type: str,
    ) -> ft.Control:
        """构建模型操作区域"""
        model_id = model["id"]
        model_name = model["name"]
        is_enhancement = model_type == "enhancement"

        if download_status == DownloadStatus.WAITING:
            # 排队中状态
            return ft.Container(
                content=ft.Row(
                    controls=[
                        ft.ProgressRing(width=12, height=12, stroke_width=2, color=self.theme.color_scheme.primary),
                        ft.Text("Waiting...", size=10, color=self.theme.color_scheme.on_surface_variant),
                        ft.Container(expand=True),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            icon_color=self.theme.color_scheme.error,
                            icon_size=16,
                            tooltip="Cancel",
                            data={"id": model_id, "name": model_name, "is_enhancement": is_enhancement},
                            on_click=self._on_cancel_click_wrapper,
                            style=ft.ButtonStyle(padding=0),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                height=55,
            )
        elif download_status == DownloadStatus.DOWNLOADING:
            # 下载中状态
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.ProgressBar(
                            expand=True,
                            height=4,
                            value=progress / 100,
                            color=self.theme.color_scheme.primary,
                            bgcolor=self.theme.color_scheme.surface_variant,
                        ),
                        ft.Container(height=4),
                        ft.Row(
                            controls=[
                                ft.Text(
                                    message if message else f"{int(progress)}%",
                                    size=9,
                                    color=self.theme.color_scheme.on_surface_variant,
                                    expand=True,
                                    no_wrap=True,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.CLOSE,
                                    icon_color=self.theme.color_scheme.error,
                                    icon_size=16,
                                    tooltip="Cancel",
                                    data={"id": model_id, "name": model_name, "is_enhancement": is_enhancement},
                                    on_click=self._on_cancel_click_wrapper,
                                    style=ft.ButtonStyle(padding=0),
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=2,
                ),
                height=55,
            )
        elif download_status == DownloadStatus.FAILED:
            # 失败状态 - 显示重试按钮
            return ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.ERROR_OUTLINE, size=16, color=self.theme.color_scheme.error),
                        ft.Text("Failed", size=10, color=self.theme.color_scheme.error),
                        ft.Container(expand=True),
                        ft.IconButton(
                            icon=ft.Icons.REFRESH,
                            icon_color=self.theme.color_scheme.primary,
                            icon_size=18,
                            tooltip="Retry",
                            data={"id": model_id, "name": model_name, "is_enhancement": is_enhancement},
                            on_click=self._on_download_click_wrapper,
                            style=ft.ButtonStyle(padding=0),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                height=55,
            )
        elif download_status == DownloadStatus.CANCELLED:
            # 取消状态 - 显示重试按钮
            return ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.CANCEL_OUTLINED, size=16, color=self.theme.color_scheme.outline),
                        ft.Text("Cancelled", size=10, color=self.theme.color_scheme.outline),
                        ft.Container(expand=True),
                        ft.IconButton(
                            icon=ft.Icons.REFRESH,
                            icon_color=self.theme.color_scheme.primary,
                            icon_size=18,
                            tooltip="Retry",
                            data={"id": model_id, "name": model_name, "is_enhancement": is_enhancement},
                            on_click=self._on_download_click_wrapper,
                            style=ft.ButtonStyle(padding=0),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                height=55,
            )
        elif self._deleting_models.get(model_id, False):
            # 删除中状态 - 显示进度指示器
            return ft.Container(
                content=ft.Row(
                    controls=[
                        ft.ProgressRing(width=14, height=14, stroke_width=2, color=self.theme.color_scheme.error),
                        ft.Text("Deleting...", size=10, color=self.theme.color_scheme.on_surface_variant),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                height=55,
            )
        elif downloaded:
            # 已下载 - 显示删除按钮
            return ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.CHECK_CIRCLE, size=16, color=SEMANTIC_COLORS["success"]),
                        ft.Text("Downloaded", size=10, color=SEMANTIC_COLORS["success"]),
                        ft.Container(expand=True),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_color=self.theme.color_scheme.error,
                            icon_size=18,
                            tooltip="Delete",
                            data={"id": model_id, "name": model_name, "is_enhancement": is_enhancement},
                            on_click=self._on_delete_click_wrapper,
                            style=ft.ButtonStyle(padding=0),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                height=55,
            )
        else:
            # 未下载 - 显示下载按钮
            return ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.CLOUD_DOWNLOAD_OUTLINED, size=16, color=self.theme.color_scheme.on_surface_variant),
                        ft.Text("Not downloaded", size=10, color=self.theme.color_scheme.on_surface_variant),
                        ft.Container(expand=True),
                        ft.IconButton(
                            icon=ft.Icons.DOWNLOAD_ROUNDED,
                            icon_color=self.theme.color_scheme.primary,
                            icon_size=18,
                            tooltip="Download",
                            data={"id": model_id, "name": model_name, "is_enhancement": is_enhancement},
                            on_click=self._on_download_click_wrapper,
                            style=ft.ButtonStyle(padding=0),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                height=55,
            )

    def _check_model_downloaded(self, model_id: str, model_type: str) -> bool:
        """检查模型是否已下载（使用统一注册表）"""
        return is_model_downloaded(model_id)

    # ==================== 下载回调 ====================

    def _on_download_state_changed(
        self, model_id: str, status: DownloadStatus, progress: float, message: str
    ) -> None:
        """DownloadManager 状态变化回调（在后台线程中调用）"""
        # 使用 page.run_thread() 在主线程中更新 UI
        # 注意：这里不能直接调用 UI 更新，需要通过 Flet 的线程安全机制
        try:
            # 使用 page 的线程安全机制
            self.page.run_thread(self._safe_refresh_page)
        except Exception as e:
            log_error(f"Failed to trigger UI refresh: {e}")

    def _safe_refresh_page(self) -> None:
        """安全刷新页面（在主线程中调用）"""
        try:
            self._refresh_page()
        except Exception as e:
            log_error(f"Failed to refresh page: {e}")

    # ==================== 模型下载相关方法 ====================

    def _on_download_click_wrapper(self, e) -> None:
        """处理下载按钮点击事件"""
        data = e.control.data
        model_id = data["id"]
        model_name = data["name"]
        is_enhancement = data.get("is_enhancement", False)
        log_info(f"Download button clicked for model: {model_id}")
        self._start_download(model_id, model_name, is_enhancement)

    def _on_cancel_click_wrapper(self, e) -> None:
        """处理取消按钮点击事件"""
        data = e.control.data
        model_id = data["id"]
        log_info(f"Cancel button clicked for model: {model_id}")
        # cancel() will properly set CANCELLED status and clean up
        self._download_manager.cancel(model_id)
        self._refresh_page()

    def _on_delete_click_wrapper(self, e) -> None:
        """处理删除按钮点击事件 - 显示确认对话框"""
        data = e.control.data
        model_id = data["id"]
        model_name = data["name"]
        is_enhancement = data.get("is_enhancement", False)
        log_info(f"Delete button clicked for model: {model_id}")
        self._show_delete_confirm_dialog(model_id, model_name, is_enhancement)

    def _show_delete_confirm_dialog(self, model_id: str, model_name: str, is_enhancement: bool) -> None:
        """显示删除确认对话框"""
        def on_confirm(e):
            self._close_dialog()
            self._delete_model(model_id, model_name, is_enhancement)

        def on_cancel(e):
            self._close_dialog()

        self._dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Delete Model"),
            content=ft.Text(
                f"Are you sure you want to delete '{model_name}'?\n\nThis action cannot be undone.",
                size=14,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=on_cancel),
                ft.TextButton(
                    "Delete",
                    on_click=on_confirm,
                    style=ft.ButtonStyle(color=self.theme.color_scheme.error),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(self._dialog)

    def _close_dialog(self) -> None:
        """关闭对话框"""
        if self._dialog:
            self.page.pop_dialog()
            self._dialog = None

    def _start_download(self, model_id: str, model_name: str, is_enhancement: bool) -> None:
        """开始下载模型（统一入口）"""
        log_info(f"Starting download for: {model_id}")

        # 所有模型统一使用 DownloadManager
        if self._download_manager.is_in_queue(model_id):
            log_info(f"Model {model_id} already in queue")
            self._show_snackbar(f"Model '{model_name}' is already in queue", self.theme.color_scheme.primary)
            return

        # Clear previous status (CANCELLED, FAILED, etc.) before starting new download
        # This allows retry after cancellation or failure
        self._download_manager.clear_status(model_id)

        # 加入下载队列
        self._download_manager.enqueue(model_id)
        self._refresh_page()

    def _delete_model(self, model_id: str, model_name: str, is_enhancement: bool) -> None:
        """删除模型"""
        log_info(f"Deleting model: {model_id}")

        # 设置删除中状态并立即刷新 UI
        self._deleting_models[model_id] = True
        self._refresh_page()

        success_color = SEMANTIC_COLORS["success"]
        error_color = self.theme.color_scheme.error

        def run_delete():
            try:
                if is_enhancement:
                    # 删除增强模型（使用统一注册表）
                    from mediafactory.models.model_registry import get_model_local_path

                    model_path = get_model_local_path(model_id)
                    if model_path and model_path.exists():
                        model_path.unlink()
                        log_info(f"Enhancement model deleted: {model_id}")
                        self._show_snackbar(f"Model '{model_name}' deleted successfully!", success_color)
                    else:
                        self._show_snackbar(f"Model file not found", error_color)
                else:
                    # 删除音频/翻译模型
                    from mediafactory.models.model_download import delete_model

                    success, error_msg = delete_model(model_id)
                    if success:
                        log_info(f"Model deleted: {model_id}")
                        self._show_snackbar(f"Model '{model_name}' deleted successfully!", success_color)
                    else:
                        log_error(f"Failed to delete model: {model_id} - {error_msg}")
                        self._show_snackbar(f"Failed to delete: {error_msg[:50]}", error_color)

            except Exception as ex:
                error_msg = str(ex)[:100]
                log_error(f"Delete failed: {error_msg}")
                self._show_snackbar(f"Delete failed: {error_msg}", error_color)

            finally:
                # 清除删除中状态
                self._deleting_models.pop(model_id, None)
                self._refresh_model_status()
                self._safe_refresh_page()

        import threading
        thread = threading.Thread(target=run_delete, daemon=True)
        thread.start()

    def _refresh_model_status(self) -> None:
        """刷新模型状态"""
        try:
            from mediafactory.config import get_config_manager
            config_manager = get_config_manager()
            config_manager.sync_models_on_startup()
            self.config = get_config()
            log_info("Model status refreshed")
        except Exception as ex:
            log_info(f"Failed to refresh model status: {ex}")

    def _refresh_page(self) -> None:
        """刷新页面（主线程调用）"""
        try:
            if self._content_column is not None:
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


def build_models_page(page: ft.Page, params: Dict[str, Any]) -> ft.Control:
    """构建 Models 页面"""
    models_page = ModelsPage(page)
    return models_page.build()
