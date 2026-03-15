"""
任务页面

采用任务队列模式，支持：
- 添加多个任务到队列
- 批量启动/取消任务
- 创建各类多媒体处理任务
"""

from typing import Dict, Any, Optional, List
import uuid
import flet as ft

from mediafactory.gui.flet.theme import get_theme
from mediafactory.gui.flet.state import (
    get_state,
    TaskItem,
    TaskStatus,
    TaskConfig,
)
from mediafactory.gui.flet.async_handler import AsyncTaskManager
from mediafactory.gui.flet.components.status_banner import show_success, show_error
from mediafactory.gui.flet.components.task_card import TaskCard
from mediafactory.gui.flet.components.task_config_dialog import (
    TaskConfigDialog,
    TASK_TYPE_NAMES,
)
# ModelStatusSection 已移至 Models 页面
from mediafactory.gui.flet.services import (
    get_subtitle_service,
    get_audio_service,
    get_transcription_service,
    get_translation_service,
    get_video_enhancement_service,
)
from mediafactory.logging import log_info, log_error_with_context
from mediafactory.utils.file_utils import open_file_location


class TasksPage:
    """任务页面管理器"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.theme = get_theme()
        self.state = get_state()
        self.task_manager = AsyncTaskManager(page)

        # 服务
        self._subtitle_service = get_subtitle_service()
        self._audio_service = get_audio_service()
        self._transcription_service = get_transcription_service()
        self._translation_service = get_translation_service()
        self._video_enhancement_service = get_video_enhancement_service()

        # UI 组件
        self._content_area: Optional[ft.Column] = None
        self._task_list: Optional[ft.Column] = None
        self._add_btn: Optional[ft.ElevatedButton] = None
        self._start_all_btn: Optional[ft.ElevatedButton] = None
        self._cancel_all_btn: Optional[ft.OutlinedButton] = None
        self._clear_all_btn: Optional[ft.OutlinedButton] = None
        # _model_status_section 已移至 Models 页面

        # 任务卡片缓存
        self._task_cards: Dict[str, TaskCard] = {}

    def build(self) -> ft.Control:
        """构建页面"""
        # 模型状态初始化已移至 Models 页面

        # 添加任务按钮
        self._add_btn = ft.ElevatedButton(
            "Add Task",
            icon=ft.Icons.ADD,
            on_click=self._on_add_task,
            bgcolor=self.theme.color_scheme.primary,
            color=self.theme.color_scheme.on_primary,
            style=ft.ButtonStyle(
                padding=ft.padding.symmetric(horizontal=10, vertical=6)
            ),
        )

        # 任务队列标题行（包含标题和所有操作按钮）
        header = ft.Row(
            controls=[
                ft.Icon(
                    ft.Icons.ASSIGNMENT_OUTLINED,
                    size=20,
                    color=self.theme.color_scheme.primary,
                ),
                ft.Text(
                    "Task Queue",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=self.theme.color_scheme.on_surface,
                ),
                ft.Container(width=12),
                # 添加任务按钮
                self._add_btn,
                ft.Container(expand=True),
                # 批量操作按钮
                self._build_start_all_btn(),
                self._build_cancel_all_btn(),
                self._build_clear_all_btn(),
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # 任务列表 - 使用ListView虚拟滚动
        self._task_list = ft.ListView(
            controls=self._build_task_cards(),
            spacing=8,
            padding=8,
            item_extent=70,  # 固定高度，启用虚拟滚动
            expand=True,
        )

        # 主布局（模型状态区域已移至 Models 页面）
        return ft.Column(
            controls=[
                # 任务队列区域
                ft.Container(
                    content=ft.Column(
                        controls=[
                            header,
                            ft.Container(height=12),
                            ft.Container(
                                content=self._task_list,
                                bgcolor=self.theme.color_scheme.surface_variant,
                                border_radius=self.theme.radius_md,
                                expand=True,
                            ),
                        ],
                        spacing=0,
                    ),
                    padding=ft.padding.all(12),
                    bgcolor=self.theme.color_scheme.surface,
                    border_radius=self.theme.radius_md,
                    border=ft.border.all(1, self.theme.color_scheme.outline_variant),
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        )

    def _build_start_all_btn(self) -> ft.Control:
        """构建启动全部按钮"""
        self._start_all_btn = ft.ElevatedButton(
            "Start All",
            icon=ft.Icons.PLAY_ARROW,
            on_click=self._on_start_all,
            bgcolor=self.theme.color_scheme.tertiary_container,
            color=self.theme.color_scheme.on_tertiary_container,
            style=ft.ButtonStyle(
                padding=ft.padding.symmetric(horizontal=10, vertical=6)
            ),
            disabled=True,
        )
        return self._start_all_btn

    def _build_cancel_all_btn(self) -> ft.Control:
        """构建取消全部按钮"""
        self._cancel_all_btn = ft.OutlinedButton(
            "Cancel All",
            icon=ft.Icons.CANCEL_OUTLINED,
            on_click=self._on_cancel_all,
            style=ft.ButtonStyle(
                padding=ft.padding.symmetric(horizontal=10, vertical=6)
            ),
            disabled=True,
        )
        return self._cancel_all_btn

    def _build_clear_all_btn(self) -> ft.Control:
        """构建清除全部按钮"""
        self._clear_all_btn = ft.OutlinedButton(
            "Clear All",
            icon=ft.Icons.DELETE_SWEEP,
            on_click=self._on_clear_all,
            style=ft.ButtonStyle(
                padding=ft.padding.symmetric(horizontal=10, vertical=6)
            ),
            disabled=True,
        )
        return self._clear_all_btn

    def _build_task_cards(self) -> List[ft.Control]:
        """构建任务卡片列表"""
        if not self.state.tasks:
            return [
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(
                                ft.Icons.INBOX_OUTLINED,
                                size=48,
                                color=self.theme.color_scheme.outline,
                            ),
                            ft.Text(
                                "No tasks yet",
                                size=14,
                                color=self.theme.color_scheme.on_surface_variant,
                            ),
                            ft.Text(
                                "Click 'Add Task' to get started",
                                size=12,
                                color=self.theme.color_scheme.outline,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    alignment=ft.Alignment(0, 0),  # center
                    height=200,
                )
            ]

        cards = []
        for task in self.state.tasks:
            card = TaskCard(
                task=task,
                on_start=self._on_start_task,
                on_cancel=self._on_cancel_task,
                on_delete=self._on_delete_task,
                on_reveal=self._on_reveal_task,
            )
            self._task_cards[task.id] = card
            cards.append(card.build())

        return cards

    def _on_add_task(self, e) -> None:
        """添加任务"""
        try:
            dialog = TaskConfigDialog(
                page=self.page,
                on_confirm=self._on_task_config_confirm,
            )
            dialog.show()
        except Exception as ex:
            log_error_with_context("Failed to open task dialog", ex, {})
            show_error(self.page, f"Failed to add task: {ex}")

    def _on_task_config_confirm(self, config: TaskConfig) -> None:
        """任务配置确认"""
        # 生成任务ID
        task_id = str(uuid.uuid4())[:8]

        # 获取任务名称
        task_name = TASK_TYPE_NAMES.get(config.task_type, config.task_type)
        if config.input_path:
            from pathlib import Path

            file_name = Path(config.input_path).name
            task_name = f"{task_name}: {file_name}"

        # 创建任务项
        task = TaskItem(
            id=task_id,
            name=task_name,
            input_path=config.input_path,
            status=TaskStatus.IDLE,
            config=config,
        )

        # 添加到状态
        self.state.add_task(task)

        # 刷新UI
        self._refresh_task_list()
        self._update_batch_buttons()

    def _on_start_task(self, task_id: str) -> None:
        """启动单个任务"""
        task = next((t for t in self.state.tasks if t.id == task_id), None)
        if not task or not task.config:
            return

        # 更新任务状态
        self.state.update_task(
            task_id, status=TaskStatus.RUNNING, progress=0, message="Starting..."
        )
        self._refresh_task_list()

        # 使用新的 execute() 方法
        import asyncio

        asyncio.create_task(
            self.task_manager.execute(
                task_id=task_id,
                name=task.name,
                coroutine=lambda cb: self._execute_task(task, cb),
                on_progress=lambda p, m: self._on_task_progress(task_id, p, m),
                on_complete=lambda r: self._on_task_complete(task_id, r),
                on_error=lambda e: self._on_task_error(task_id, e),
            )
        )

        self._update_batch_buttons()

    def _on_cancel_task(self, task_id: str) -> None:
        """取消任务"""
        self.task_manager.cancel_task(task_id)
        self.state.update_task(
            task_id, status=TaskStatus.CANCELLED, message="Cancelled"
        )
        self._refresh_task_list()
        self._update_batch_buttons()

    def _on_delete_task(self, task_id: str) -> None:
        """删除任务"""
        self.state.remove_task(task_id)
        if task_id in self._task_cards:
            del self._task_cards[task_id]
        self._refresh_task_list()
        self._update_batch_buttons()

    def _on_reveal_task(self, task_id: str) -> None:
        """在文件管理器中显示任务输出"""
        task = next((t for t in self.state.tasks if t.id == task_id), None)
        if not task or not task.output_path:
            show_error(self.page, "No output file available")
            return

        success = open_file_location(task.output_path)
        if not success:
            show_error(self.page, f"File not found: {task.output_path}")

    def _on_start_all(self, e) -> None:
        """启动所有待执行的任务"""
        for task in self.state.tasks:
            if task.status in [TaskStatus.IDLE, TaskStatus.PENDING]:
                self._on_start_task(task.id)

    def _on_cancel_all(self, e) -> None:
        """取消所有运行中的任务"""
        for task in self.state.tasks:
            if task.status == TaskStatus.RUNNING:
                self._on_cancel_task(task.id)

    def _on_clear_all(self, e) -> None:
        """清除所有已完成/失败/取消的任务"""
        # 收集要删除的任务ID
        to_remove = [
            t.id
            for t in self.state.tasks
            if t.status
            in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
        ]
        # 删除任务
        for task_id in to_remove:
            self.state.remove_task(task_id)
            if task_id in self._task_cards:
                del self._task_cards[task_id]
        # 刷新UI
        self._refresh_task_list()
        self._update_batch_buttons()

    async def _execute_task(self, task: TaskItem, progress_callback) -> Dict[str, Any]:
        """执行任务"""
        config = task.config
        if not config:
            return {"success": False, "error": "No task config"}

        def _result_to_dict(result) -> Dict[str, Any]:
            """将 ProcessingResult 转换为字典"""
            if isinstance(result, dict):
                return result
            # ProcessingResult dataclass
            return {
                "success": result.success,
                "output_path": result.output_path,
                "error": result.error if hasattr(result, "error") else None,
                "error_type": (
                    result.error_type if hasattr(result, "error_type") else None
                ),
                "error_context": (
                    result.error_context if hasattr(result, "error_context") else None
                ),
                "metadata": result.metadata if hasattr(result, "metadata") else {},
            }

        try:
            if config.task_type == "subtitle":
                result = await self._subtitle_service.generate_subtitles(
                    video_path=config.input_path,
                    page=self.page,
                    source_language=config.source_lang,
                    target_language=config.target_lang,
                    use_llm=config.use_llm,
                    llm_preset=config.llm_preset,
                    output_format_type=config.output_format_type,
                    bilingual=config.bilingual,
                    bilingual_layout=config.bilingual_layout,
                    style_preset=config.style_preset,
                    progress_callback=progress_callback,
                )
                return _result_to_dict(result)
            elif config.task_type == "audio":
                result = await self._audio_service.extract_audio(
                    video_path=config.input_path,
                    page=self.page,
                    output_format=config.output_format,
                    sample_rate=config.sample_rate,
                    channels=config.channels,
                    filter_enabled=config.filter_enabled,
                    highpass_freq=config.highpass_freq,
                    lowpass_freq=config.lowpass_freq,
                    volume=config.volume,
                    progress_callback=progress_callback,
                )
                return _result_to_dict(result)
            elif config.task_type == "transcription":
                result = await self._transcription_service.transcribe(
                    audio_path=config.input_path,
                    page=self.page,
                    language=config.source_lang,
                    output_format_type=config.output_format_type,
                    bilingual=config.bilingual,
                    bilingual_layout=config.bilingual_layout,
                    style_preset=config.style_preset,
                    progress_callback=progress_callback,
                )
                return _result_to_dict(result)
            elif config.task_type == "subtitle_translation":
                result = await self._translation_service.translate_srt(
                    srt_path=config.input_path,
                    page=self.page,
                    target_lang=config.target_lang,
                    use_llm=config.use_llm,
                    progress_callback=progress_callback,
                )
                return _result_to_dict(result)
            elif config.task_type == "video_enhancement":
                result = await self._video_enhancement_service.enhance_video(
                    video_path=config.input_path,
                    page=self.page,
                    preset=config.enhancement_preset,
                    scale=config.enhancement_scale,
                    model_type=config.enhancement_model,
                    denoise=config.enhancement_denoise,
                    face_fix=config.enhancement_face_fix,
                    temporal=config.enhancement_temporal,
                    progress_callback=progress_callback,
                )
                return _result_to_dict(result)

            return {"success": False, "error": "Unknown task type"}
        except Exception as ex:
            return {"success": False, "error": str(ex)}

    def _on_task_progress(
        self, task_id: str, progress: float, message: str = ""
    ) -> None:
        """任务进度更新"""
        self.state.update_task(
            task_id,
            progress=progress,
            message=message,
        )
        # 使用增量更新代替重建整个列表
        task_card = self._task_cards.get(task_id)
        if task_card:
            try:
                # 从任务列表中查找任务
                task = next((t for t in self.state.tasks if t.id == task_id), None)
                if task:
                    task_card.update_task(task)
                    task_card.update_ui()
            except Exception as e:
                log_error_with_context("Failed to update task card", e, {"task_id": task_id})

    def _on_task_complete(self, task_id: str, result: Dict[str, Any]) -> None:
        """任务完成"""
        if result.get("success"):
            self.state.update_task(
                task_id,
                status=TaskStatus.COMPLETED,
                progress=100,
                message="Completed",
                output_path=result.get("output_path"),
            )
            output = result.get("output_path") or result.get("output") or "Done"
            try:
                show_success(self.page, f"Task completed: {output}")
            except Exception as e:
                log_error_with_context("Failed to show success banner", e, {})
        else:
            self.state.update_task(
                task_id,
                status=TaskStatus.FAILED,
                message=result.get("error", "Unknown error"),
                error=result.get("error", "Unknown error"),
                error_type=result.get("error_type"),
                error_context=result.get("error_context"),
            )
            # 不再显示 Banner，错误信息通过 Tooltip 在任务卡片上显示

        self._refresh_task_list()
        self._update_batch_buttons()

    def _on_task_error(self, task_id: str, error: str) -> None:
        """任务错误"""
        self.state.update_task(
            task_id,
            status=TaskStatus.FAILED,
            message=error,
        )
        try:
            show_error(self.page, f"Task error: {error}")
        except Exception as e:
            log_error_with_context("Failed to show error banner", e, {})
        self._refresh_task_list()
        self._update_batch_buttons()

    def _refresh_task_list(self) -> None:
        """刷新任务列表"""
        if self._task_list:
            try:
                self._task_cards.clear()
                self._task_list.controls = self._build_task_cards()
                # 使用 page.update() 而不是 control.update()
                # 这样更安全，可以同时更新整个页面
                self.page.update()
            except Exception as e:
                # 如果更新失败，记录错误但不影响其他流程
                log_error_with_context("Failed to refresh task list", e, {})

    def _update_batch_buttons(self) -> None:
        """更新批量操作按钮状态"""
        has_idle = any(
            t.status in [TaskStatus.IDLE, TaskStatus.PENDING] for t in self.state.tasks
        )
        has_running = any(t.status == TaskStatus.RUNNING for t in self.state.tasks)
        has_cleared_status = any(
            t.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
            for t in self.state.tasks
        )

        # 使用 page.update() 代替单个控件 update()，避免控件未添加到页面时报错
        try:
            if self._start_all_btn:
                self._start_all_btn.disabled = not has_idle
            if self._cancel_all_btn:
                self._cancel_all_btn.disabled = not has_running
            if self._clear_all_btn:
                self._clear_all_btn.disabled = not has_cleared_status or has_running
            self.page.update()
        except Exception:
            pass  # 页面可能已切换，忽略更新错误


def build_tasks_page(page: ft.Page, params: Dict[str, Any]) -> ft.Control:
    """构建任务页面"""
    tasks_page = TasksPage(page)
    return tasks_page.build()
