"""
任务卡片组件

显示单个任务的配置摘要、状态和操作按钮。
优化布局：3行紧凑设计，高度约70px。
"""

from typing import Optional, Callable, Dict, Any
import platform
import flet as ft

from mediafactory.gui.flet.theme import get_theme
from mediafactory.gui.flet.state import TaskItem, TaskStatus, TaskConfig
from mediafactory.gui.flet.components.task_config_dialog import TASK_TYPE_NAMES


class TaskCard:
    """任务卡片组件 - 紧凑3行布局"""

    def __init__(
        self,
        task: TaskItem,
        on_start: Optional[Callable[[str], None]] = None,
        on_cancel: Optional[Callable[[str], None]] = None,
        on_delete: Optional[Callable[[str], None]] = None,
        on_reveal: Optional[Callable[[str], None]] = None,
    ):
        self.task = task
        self.on_start = on_start
        self.on_cancel = on_cancel
        self.on_delete = on_delete
        self.on_reveal = on_reveal
        self.theme = get_theme()
        self._component: Optional[ft.Control] = None

    def build(self) -> ft.Control:
        """构建组件 - 紧凑3行布局"""
        is_running = self.task.status == TaskStatus.RUNNING
        is_completed = self.task.status == TaskStatus.COMPLETED
        is_failed = self.task.status == TaskStatus.FAILED
        is_cancelled = self.task.status == TaskStatus.CANCELLED
        is_finished = is_completed or is_failed or is_cancelled

        # 状态颜色
        status_colors = {
            TaskStatus.RUNNING: self.theme.color_scheme.primary,
            TaskStatus.COMPLETED: self.theme.color_scheme.tertiary,
            TaskStatus.FAILED: self.theme.color_scheme.error,
            TaskStatus.CANCELLED: self.theme.color_scheme.outline,
            TaskStatus.PENDING: self.theme.color_scheme.tertiary,
            TaskStatus.IDLE: self.theme.color_scheme.outline,
        }
        status_color = status_colors.get(
            self.task.status, self.theme.color_scheme.outline
        )

        # 状态文本
        status_text = {
            TaskStatus.RUNNING: "Running",
            TaskStatus.COMPLETED: "Done",
            TaskStatus.FAILED: "Failed",
            TaskStatus.CANCELLED: "Cancelled",
            TaskStatus.PENDING: "Pending",
            TaskStatus.IDLE: "Ready",
        }.get(self.task.status, "Unknown")

        # 配置摘要
        config_summary = self._get_config_summary()

        # 操作按钮
        action_buttons = []

        if not is_running and not is_finished:
            action_buttons.append(
                ft.IconButton(
                    icon=ft.Icons.PLAY_ARROW,
                    icon_size=16,
                    tooltip="Start",
                    on_click=lambda e: self._on_start_click(),
                    style=ft.ButtonStyle(
                        color=self.theme.color_scheme.primary,
                        padding=4,
                    ),
                )
            )

        if is_running:
            action_buttons.append(
                ft.IconButton(
                    icon=ft.Icons.CANCEL_OUTLINED,
                    icon_size=16,
                    tooltip="Cancel",
                    on_click=lambda e: self._on_cancel_click(),
                    style=ft.ButtonStyle(
                        color=self.theme.color_scheme.error,
                        padding=4,
                    ),
                )
            )

        reveal_tooltip = (
            "Reveal in Finder" if platform.system() == "Darwin" else "Show in Explorer"
        )
        if is_completed and self.task.output_path:
            action_buttons.append(
                ft.IconButton(
                    icon=ft.Icons.FOLDER_OPEN_OUTLINED,
                    icon_size=16,
                    tooltip=reveal_tooltip,
                    on_click=lambda e: self._on_reveal_click(),
                    style=ft.ButtonStyle(
                        color=self.theme.color_scheme.primary,
                        padding=4,
                    ),
                )
            )

        # IDLE 状态也显示删除按钮
        if not is_running and not is_finished:
            action_buttons.append(
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINED,
                    icon_size=16,
                    tooltip="Delete",
                    on_click=lambda e: self._on_delete_click(),
                    style=ft.ButtonStyle(
                        color=self.theme.color_scheme.on_surface_variant,
                        padding=4,
                    ),
                )
            )

        if is_finished:
            action_buttons.append(
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINED,
                    icon_size=16,
                    tooltip="Delete",
                    on_click=lambda e: self._on_delete_click(),
                    style=ft.ButtonStyle(
                        color=self.theme.color_scheme.on_surface_variant,
                        padding=4,
                    ),
                )
            )

        # 第一行：图标 + 名称 + 状态 + 摘要 + 按钮
        # 状态徽章
        status_badge = ft.Container(
            content=ft.Text(
                status_text,
                size=10,
                color=status_color,
                weight=ft.FontWeight.W_500,
            ),
            padding=ft.padding.symmetric(horizontal=6, vertical=1),
            bgcolor=self._get_status_bgcolor(status_color),
            border_radius=self.theme.radius_sm,
        )

        # 失败状态：状态徽章 + 错误图标组合
        if is_failed and self.task.error:
            status_display = ft.Row(
                controls=[
                    status_badge,
                    ft.Container(
                        content=ft.Icon(
                            ft.Icons.ERROR_OUTLINE,
                            size=14,
                            color=self.theme.color_scheme.error,
                        ),
                        tooltip=self._format_error_tooltip(),
                    ),
                ],
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        else:
            # 其他状态：仅状态徽章
            status_display = status_badge

        row1_controls = [
            ft.Icon(
                self._get_task_icon(),
                size=16,
                color=status_color,
            ),
            ft.Text(
                self.task.name,
                size=12,
                weight=ft.FontWeight.W_500,
                color=self.theme.color_scheme.on_surface,
                expand=True,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
            status_display,
        ]

        # 添加配置摘要（紧凑显示）
        if config_summary:
            row1_controls.append(
                ft.Text(
                    f" • {config_summary}",
                    size=10,
                    color=self.theme.color_scheme.on_surface_variant,
                    overflow=ft.TextOverflow.ELLIPSIS,
                )
            )

        # 添加操作按钮
        row1_controls.extend(action_buttons)

        # 第二行：进度条 + 进度百分比 + 消息
        row2_controls = []
        if is_running:
            row2_controls = [
                ft.ProgressBar(
                    value=self.task.progress / 100 if self.task.progress > 0 else None,
                    bar_height=3,
                    color=status_color,
                    bgcolor=self.theme.color_scheme.surface_variant,
                    expand=True,
                ),
                ft.Text(
                    f"{self.task.progress:.0f}%",
                    size=10,
                    color=status_color,
                ),
            ]
            if self.task.message:
                row2_controls.append(
                    ft.Text(
                        f" • {self.task.message}",
                        size=10,
                        color=self.theme.color_scheme.on_surface_variant,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    )
                )

        # 构建列控件
        column_controls = [
            ft.Row(
                controls=row1_controls,
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ]

        # 添加第二行（运行中或有进度时）
        if row2_controls:
            column_controls.append(
                ft.Row(
                    controls=row2_controls,
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )

        # 主容器 - 紧凑padding
        self._component = ft.Container(
            content=ft.Column(
                controls=column_controls,
                spacing=4,
            ),
            padding=ft.padding.all(8),
            bgcolor=self.theme.color_scheme.surface,
            border_radius=self.theme.radius_md,
            border=ft.border.all(1, self.theme.color_scheme.outline_variant),
            opacity=0.7 if is_cancelled else 1.0,
        )

        return self._component

    def _get_task_icon(self) -> str:
        """获取任务图标"""
        icons = {
            "subtitle": ft.Icons.SUBTITLES,
            "audio": ft.Icons.AUDIO_FILE,
            "transcription": ft.Icons.MIC,
            "subtitle_translation": ft.Icons.SUBTITLES_OUTLINED,
        }
        if self.task.config:
            return icons.get(self.task.config.task_type, ft.Icons.TASK)
        return ft.Icons.TASK

    def _get_config_summary(self) -> str:
        """获取配置摘要"""
        if not self.task.config:
            return ""

        config = self.task.config
        task_type = TASK_TYPE_NAMES.get(config.task_type, config.task_type)

        if config.task_type == "subtitle":
            lang_info = f"{config.source_lang}→{config.target_lang}"
            parts = [lang_info]
            # 显示输出格式
            fmt = config.output_format_type.upper()
            if fmt == "ASS":
                # 显示样式预设
                style = getattr(config, "style_preset", "default")
                if style != "default":
                    parts.append(f"ASS ({style})")
                else:
                    parts.append("ASS")
            elif fmt != "SRT":
                parts.append(fmt)
            # 显示双语
            if config.bilingual:
                parts.append("Bilingual")
            return " ".join(parts)
        elif config.task_type == "audio":
            return f"{config.output_format.upper()}"
        elif config.task_type == "transcription":
            parts = []
            # 显示输出格式
            fmt = config.output_format_type.upper()
            if fmt == "ASS":
                style = getattr(config, "style_preset", "default")
                if style != "default":
                    parts.append(f"ASS ({style})")
                else:
                    parts.append("ASS")
            elif fmt != "SRT":
                parts.append(fmt)
            # 显示双语
            if config.bilingual:
                parts.append("Bilingual")
            return " ".join(parts) if parts else "Auto"
        elif config.task_type == "subtitle_translation":
            return f"→{config.target_lang}"

        return task_type

    def _format_error_tooltip(self) -> str:
        """格式化错误提示信息"""
        if not self.task.error:
            return "Unknown error"

        lines = [f"{self.task.error}"]

        if self.task.error_type:
            lines.append(f"\nType: {self.task.error_type}")

        if self.task.error_context:
            context = self.task.error_context
            if "backend" in context:
                lines.append(f"Backend: {context['backend']}")
            if "model" in context:
                lines.append(f"Model: {context['model']}")
            if "src_lang" in context and "tgt_lang" in context:
                lines.append(
                    f"Languages: {context['src_lang']} → {context['tgt_lang']}"
                )

        return "\n".join(lines)

    def _get_status_bgcolor(self, status_color: str) -> str:
        """获取状态背景色"""
        if status_color == self.theme.color_scheme.primary:
            return self.theme.color_scheme.primary_container
        elif status_color == self.theme.color_scheme.tertiary:
            return self.theme.color_scheme.tertiary_container
        elif status_color == self.theme.color_scheme.error:
            return self.theme.color_scheme.error_container
        return self.theme.color_scheme.surface_variant

    def _on_start_click(self) -> None:
        """启动按钮点击"""
        if self.on_start:
            self.on_start(self.task.id)

    def _on_cancel_click(self) -> None:
        """取消按钮点击"""
        if self.on_cancel:
            self.on_cancel(self.task.id)

    def _on_delete_click(self) -> None:
        """删除按钮点击"""
        if self.on_delete:
            self.on_delete(self.task.id)

    def _on_reveal_click(self) -> None:
        """Reveal 按钮点击"""
        if self.on_reveal:
            self.on_reveal(self.task.id)

    def update_task(self, task: TaskItem) -> None:
        """更新任务数据"""
        self.task = task

    def update_ui(self) -> None:
        """增量更新UI组件（不重建整个组件）

        直接更新已渲染的组件属性，避免重建整个列表。
        适用于高频进度更新场景。

        Raises:
            RuntimeError: 当组件结构需要完全重建时抛出（如状态变化）
        """
        if not self._component:
            return

        try:
            # 获取内部组件引用
            container = self._component
            column = container.content
            if not column or not column.controls:
                return

            row1 = column.controls[0]

            # 状态颜色映射
            status_colors = {
                TaskStatus.RUNNING: self.theme.color_scheme.primary,
                TaskStatus.COMPLETED: self.theme.color_scheme.tertiary,
                TaskStatus.FAILED: self.theme.color_scheme.error,
                TaskStatus.CANCELLED: self.theme.color_scheme.outline,
                TaskStatus.PENDING: self.theme.color_scheme.tertiary,
                TaskStatus.IDLE: self.theme.color_scheme.outline,
            }
            status_color = status_colors.get(
                self.task.status, self.theme.color_scheme.outline
            )

            # 状态文本映射
            status_text_map = {
                TaskStatus.RUNNING: "Running",
                TaskStatus.COMPLETED: "Done",
                TaskStatus.FAILED: "Failed",
                TaskStatus.CANCELLED: "Cancelled",
                TaskStatus.PENDING: "Pending",
                TaskStatus.IDLE: "Ready",
            }
            status_text = status_text_map.get(self.task.status, "Unknown")

            # 更新第一行中的图标颜色（第1个控件）
            if row1.controls:
                icon_ctrl = row1.controls[0]
                if isinstance(icon_ctrl, ft.Icon):
                    icon_ctrl.color = status_color

            # 更新状态徽章（第3个控件，索引2）
            if len(row1.controls) > 2:
                status_badge = row1.controls[2]
                if isinstance(status_badge, ft.Container):
                    badge_text = status_badge.content
                    if isinstance(badge_text, ft.Text):
                        badge_text.value = status_text
                        badge_text.color = status_color

                    status_badge.bgcolor = self._get_status_bgcolor(status_color)
                    status_badge.tooltip = (
                        self._format_error_tooltip()
                        if self.task.status == TaskStatus.FAILED and self.task.error
                        else None
                    )

            # 更新第二行（进度条行）
            is_running = self.task.status == TaskStatus.RUNNING
            has_second_row = len(column.controls) >= 2

            if is_running:
                # 如果第二行不存在，需要重建组件
                if not has_second_row:
                    # 标记需要重建，让 TasksPage 处理
                    raise RuntimeError("Component needs rebuild for running state")

                row2 = column.controls[1]
                if not isinstance(row2, ft.Row):
                    return

                row2_controls = row2.controls

                # 更新进度条（第1个控件）
                if row2_controls:
                    progress_bar = row2_controls[0]
                    if isinstance(progress_bar, ft.ProgressBar):
                        progress_bar.value = (
                            self.task.progress / 100 if self.task.progress > 0 else None
                        )
                        progress_bar.color = status_color

                # 更新百分比文本（第2个控件）
                if len(row2_controls) > 1:
                    percent_text = row2_controls[1]
                    if isinstance(percent_text, ft.Text):
                        percent_text.value = f"{self.task.progress:.0f}%"
                        percent_text.color = status_color

                # 更新消息文本（第3个控件）
                if len(row2_controls) > 2:
                    msg_text = row2_controls[2]
                    if isinstance(msg_text, ft.Text):
                        msg_text.value = (
                            f" • {self.task.message}" if self.task.message else ""
                        )
            else:
                # 任务不在运行状态，但组件仍有第二行（进度条）
                # 这意味着状态从 RUNNING 变为 COMPLETED/FAILED/CANCELLED
                # 需要重建组件以移除进度条
                if has_second_row:
                    raise RuntimeError("Component needs rebuild for finished state")

            # 更新容器透明度（取消状态变淡）
            container.opacity = 0.7 if self.task.status == TaskStatus.CANCELLED else 1.0

            # 触发UI更新
            self._component.update()

        except RuntimeError:
            # 重新抛出 RuntimeError，让 TasksPage 捕获并处理重建
            raise
        except Exception:
            # 其他异常，标记需要重建
            self._component = None
