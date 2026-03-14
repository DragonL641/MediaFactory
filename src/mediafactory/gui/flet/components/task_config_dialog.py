"""
任务配置对话框

分两步完成配置：
1. 选择任务类型
2. 配置任务参数
"""

from typing import Dict, Any, Optional, Callable, List
import flet as ft

from mediafactory.gui.flet.theme import get_theme
from mediafactory.gui.flet.state import TaskConfig
from mediafactory.config import get_config
from mediafactory.constants import BackendConfigMapping


# 语言选项
LANGUAGES = {
    "auto": "Auto Detect",
    "en": "English",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "ru": "Russian",
}

# 目标语言（不含auto）
TARGET_LANGUAGES = {k: v for k, v in LANGUAGES.items() if k != "auto"}

# 音频采样率选项
SAMPLE_RATE_OPTIONS = [
    {"value": 48000, "label": "48000 Hz (Best)"},
    {"value": 44100, "label": "44100 Hz (CD Quality)"},
    {"value": 22050, "label": "22050 Hz"},
    {"value": 16000, "label": "16000 Hz (Speech)"},
]

# 声道选项
CHANNEL_OPTIONS = [
    {"value": 2, "label": "Stereo (2ch)"},
    {"value": 1, "label": "Mono (1ch)"},
]

# 输出格式选项（音频）
OUTPUT_FORMAT_OPTIONS = [
    {"value": "wav", "label": "WAV (Best Quality)"},
    {"value": "mp3", "label": "MP3 (Smaller Size)"},
    {"value": "flac", "label": "FLAC (Lossless)"},
    {"value": "aac", "label": "AAC (Compressed)"},
]

# 转录/字幕输出格式选项
OUTPUT_FORMAT_TYPE_OPTIONS = [
    {"value": "srt", "label": "SRT Subtitles"},
    {"value": "ass", "label": "ASS Subtitles (Styled)"},
    {"value": "txt", "label": "Plain Text (.txt)"},
]

# 字幕任务专用输出格式（SRT和ASS）
SUBTITLE_OUTPUT_FORMAT_OPTIONS = [
    {"value": "srt", "label": "SRT Subtitles"},
    {"value": "ass", "label": "ASS Subtitles (Styled)"},
]

# 双语布局选项
BILINGUAL_LAYOUT_OPTIONS = [
    {"value": "translate_on_top", "label": "Translation on Top"},
    {"value": "original_on_top", "label": "Original on Top"},
    {"value": "only_translate", "label": "Only Translation"},
    {"value": "only_original", "label": "Only Original"},
]

# ASS字幕样式预设选项
ASS_STYLE_PRESETS = [
    {"value": "default", "label": "Default"},
    {"value": "科普风", "label": "Science (科普风)"},
    {"value": "番剧风", "label": "Anime (番剧风)"},
    {"value": "新闻风", "label": "News (新闻风)"},
]

# 任务类型定义
TASK_TYPES = [
    {
        "id": "audio",
        "name": "Audio Extractor",
        "icon": ft.Icons.AUDIO_FILE,
        "desc": "Extract audio from video files",
        "input_type": "video",
    },
    {
        "id": "transcription",
        "name": "Speech to Text",
        "icon": ft.Icons.MIC,
        "desc": "Convert speech to text (SRT format)",
        "input_type": "audio_video",
    },
    {
        "id": "subtitle_translation",
        "name": "Subtitle Translator",
        "icon": ft.Icons.SUBTITLES_OUTLINED,
        "desc": "Translate SRT subtitle files",
        "input_type": "srt",
    },
    {
        "id": "subtitle",
        "name": "Subtitle Generator",
        "icon": ft.Icons.SUBTITLES,
        "desc": "Generate subtitles from video files",
        "input_type": "video",
    },
    {
        "id": "video_enhancement",
        "name": "Video Enhancement",
        "icon": ft.Icons.HIGH_QUALITY,
        "desc": "Enhance video quality with AI upscaling",
        "input_type": "video",
    },
]

# 任务类型名称映射
TASK_TYPE_NAMES = {t["id"]: t["name"] for t in TASK_TYPES}

# 文件类型过滤配置
FILE_FILTERS = {
    "video": {
        "extensions": ["mp4", "avi", "mov", "mkv", "wmv", "flv", "webm"],
        "dialog_title": "Select Video File",
    },
    "audio_video": {
        "extensions": [
            "mp4",
            "avi",
            "mov",
            "mkv",
            "wav",
            "mp3",
            "m4a",
            "flac",
            "webm",
            "ogg",
        ],
        "dialog_title": "Select Audio or Video File",
    },
    "srt": {
        "extensions": ["srt"],
        "dialog_title": "Select SRT Subtitle File",
    },
}

# 视频增强预设选项
ENHANCEMENT_PRESET_OPTIONS = [
    {"value": "fast", "label": "Fast (Upscaling Only)"},
    {"value": "balanced", "label": "Balanced (+ Denoise + Face)"},
    {"value": "quality", "label": "Quality (Full Enhancement)"},
]

# 视频增强模型类型选项
ENHANCEMENT_MODEL_OPTIONS = [
    {"value": "general", "label": "General (Recommended)"},
    {"value": "anime", "label": "Anime"},
]

# 视频增强放大倍数选项
ENHANCEMENT_SCALE_OPTIONS = [
    {"value": 2, "label": "2x"},
    {"value": 4, "label": "4x"},
]


class TaskConfigDialog:
    """任务配置对话框"""

    def __init__(
        self,
        page: ft.Page,
        on_confirm: Callable[[TaskConfig], None],
        on_cancel: Optional[Callable[[], None]] = None,
    ):
        self.page = page
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.theme = get_theme()

        # 状态
        self._step: int = 1  # 1: 选择类型, 2: 配置参数
        self._selected_type: Optional[str] = None
        self._config: Dict[str, Any] = {}

        # UI 组件
        self._dialog: Optional[ft.AlertDialog] = None
        self._content: Optional[ft.Control] = None

    def show(self) -> None:
        """显示对话框"""
        try:
            self._step = 1
            self._build_dialog()
            self.page.show_dialog(self._dialog)
        except Exception as ex:
            from mediafactory.logging import log_error_with_context

            log_error_with_context("Failed to show task dialog", ex, {})
            raise

    def close(self) -> None:
        """关闭对话框"""
        if self._dialog:
            self.page.pop_dialog()
            self._dialog = None

    def _build_dialog(self) -> None:
        """构建/重建对话框"""
        if self._step == 1:
            content = self._build_step1()
        else:
            content = self._build_step2()

        self._dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Add New Task"),
            content=content,
            actions=self._build_actions(),
            actions_alignment=ft.MainAxisAlignment.END,
            on_dismiss=lambda e: self._on_dismiss(),
        )

    def _rebuild_and_show(self) -> None:
        """重建并显示对话框"""
        # 先关闭旧的
        if self._dialog:
            self.page.pop_dialog()

        # 构建新的并显示
        self._build_dialog()
        self.page.show_dialog(self._dialog)

    def _build_step1(self) -> ft.Control:
        """构建步骤1：选择任务类型"""
        self._step = 1

        # 任务类型选择按钮
        type_buttons = []
        for task_type in TASK_TYPES:
            tid = task_type["id"]
            btn = ft.GestureDetector(
                content=ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(
                                task_type["icon"],
                                size=24,
                                color=self.theme.color_scheme.primary,
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text(
                                        task_type["name"],
                                        size=14,
                                        weight=ft.FontWeight.W_500,
                                        color=self.theme.color_scheme.on_surface,
                                    ),
                                    ft.Text(
                                        task_type["desc"],
                                        size=11,
                                        color=self.theme.color_scheme.on_surface_variant,
                                    ),
                                ],
                                spacing=2,
                            ),
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.padding.all(12),
                    bgcolor=self.theme.color_scheme.surface_variant,
                    border_radius=self.theme.radius_md,
                    border=ft.border.all(1, self.theme.color_scheme.outline_variant),
                ),
                on_tap=lambda e, t=tid: self._on_type_select(t),
                mouse_cursor=ft.MouseCursor.CLICK,
            )
            type_buttons.append(btn)

        return ft.Column(
            controls=[
                ft.Text(
                    "Select task type:",
                    size=13,
                    color=self.theme.color_scheme.on_surface_variant,
                ),
                ft.Container(height=8),
                ft.Column(controls=type_buttons, spacing=8),
            ],
            spacing=0,
            width=400,
        )

    def _build_step2(self) -> ft.Control:
        """构建步骤2：配置参数"""
        self._step = 2
        task_type = next(
            (t for t in TASK_TYPES if t["id"] == self._selected_type), None
        )
        if not task_type:
            return ft.Text("Error: Unknown task type")

        controls = [
            ft.Row(
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        on_click=lambda e: self._go_back(),
                        icon_size=20,
                    ),
                    ft.Text(
                        task_type["name"],
                        size=16,
                        weight=ft.FontWeight.W_500,
                        color=self.theme.color_scheme.on_surface,
                    ),
                ],
                spacing=8,
            ),
            ft.Container(height=12),
        ]

        # 根据任务类型添加不同的配置项
        if self._selected_type == "subtitle":
            controls.extend(self._build_subtitle_config())
        elif self._selected_type == "audio":
            controls.extend(self._build_audio_config())
        elif self._selected_type == "transcription":
            controls.extend(self._build_transcription_config())
        elif self._selected_type == "subtitle_translation":
            controls.extend(self._build_subtitle_translation_config())
        elif self._selected_type == "video_enhancement":
            controls.extend(self._build_video_enhancement_config())

        return ft.Column(
            controls=controls,
            spacing=0,
            width=480,
            scroll=ft.ScrollMode.AUTO,
        )

    def _build_subtitle_config(self) -> List[ft.Control]:
        """字幕生成配置"""
        self._input_path_field = ft.TextField(
            label="Video File Path",
            hint_text="Enter path or click Browse to select file",
            border_color=self.theme.color_scheme.outline,
            expand=True,
        )
        self._target_lang_dropdown = ft.Dropdown(
            label="Target Language",
            options=[ft.dropdown.Option(k, v) for k, v in TARGET_LANGUAGES.items()],
            value="zh",
            width=200,
            border_color=self.theme.color_scheme.outline,
        )

        # 输出格式选择 - SRT和ASS
        self._output_format_type_dropdown = ft.Dropdown(
            label="Output Format",
            options=[
                ft.dropdown.Option(opt["value"], opt["label"])
                for opt in SUBTITLE_OUTPUT_FORMAT_OPTIONS
            ],
            value="srt",
            width=200,
            border_color=self.theme.color_scheme.outline,
            on_select=self._on_output_format_change,
        )

        # ASS样式预设下拉框（仅ASS格式时显示）
        self._style_preset_dropdown = ft.Dropdown(
            label="Style Preset",
            options=[
                ft.dropdown.Option(opt["value"], opt["label"])
                for opt in ASS_STYLE_PRESETS
            ],
            value="default",
            width=200,
            visible=False,
            border_color=self.theme.color_scheme.outline,
        )

        # 双语字幕开关
        self._bilingual_switch = ft.Switch(
            label="Bilingual Subtitles",
            value=False,
            on_change=self._on_bilingual_switch_change,
            active_color=self.theme.color_scheme.primary,
        )

        # 双语布局下拉框
        self._bilingual_layout_dropdown = ft.Dropdown(
            label="Layout",
            options=[
                ft.dropdown.Option(opt["value"], opt["label"])
                for opt in BILINGUAL_LAYOUT_OPTIONS
            ],
            value="translate_on_top",
            width=200,
            visible=False,
            border_color=self.theme.color_scheme.outline,
        )

        # LLM 选项
        self._use_llm_switch = ft.Switch(
            label="Use Remote LLM for translation",
            value=False,
            on_change=self._on_llm_switch_change,
            active_color=self.theme.color_scheme.primary,
        )

        # 构建 LLM 下拉框选项
        llm_options = self._build_llm_dropdown_options()
        self._llm_preset_dropdown = ft.Dropdown(
            label="LLM Provider",
            options=llm_options,
            value="openai",
            width=280,
            visible=False,
            border_color=self.theme.color_scheme.outline,
        )

        return [
            ft.Text(
                "Input",
                size=13,
                weight=ft.FontWeight.W_500,
                color=self.theme.color_scheme.on_surface,
            ),
            ft.Row(
                controls=[
                    self._input_path_field,
                    ft.IconButton(
                        icon=ft.Icons.FOLDER_OPEN,
                        tooltip="Browse",
                        on_click=lambda e: self._on_browse_click("video"),
                        icon_color=self.theme.color_scheme.primary,
                    ),
                ],
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Container(height=16),
            ft.Text(
                "Output",
                size=13,
                weight=ft.FontWeight.W_500,
                color=self.theme.color_scheme.on_surface,
            ),
            ft.Row(
                controls=[
                    self._output_format_type_dropdown,
                ],
                spacing=12,
            ),
            self._style_preset_dropdown,  # ASS样式预设
            self._bilingual_switch,
            self._bilingual_layout_dropdown,
            ft.Container(height=16),
            ft.Text(
                "Language",
                size=13,
                weight=ft.FontWeight.W_500,
                color=self.theme.color_scheme.on_surface,
            ),
            ft.Row(
                controls=[
                    ft.Text(
                        "Auto Detect →",
                        size=13,
                        color=self.theme.color_scheme.on_surface_variant,
                    ),
                    self._target_lang_dropdown,
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Container(height=16),
            ft.Text(
                "Translation",
                size=13,
                weight=ft.FontWeight.W_500,
                color=self.theme.color_scheme.on_surface,
            ),
            self._use_llm_switch,
            self._llm_preset_dropdown,
        ]

    def _build_audio_config(self) -> List[ft.Control]:
        """音频提取配置"""
        self._input_path_field = ft.TextField(
            label="Video File Path",
            hint_text="Enter path or click Browse",
            border_color=self.theme.color_scheme.outline,
            expand=True,
        )

        # 输出格式下拉框
        self._format_dropdown = ft.Dropdown(
            label="Output Format",
            value="wav",
            options=[
                ft.dropdown.Option(key=opt["value"], text=opt["label"])
                for opt in OUTPUT_FORMAT_OPTIONS
            ],
            border_color=self.theme.color_scheme.outline,
            expand=True,
        )

        # 采样率下拉框
        self._sample_rate_dropdown = ft.Dropdown(
            label="Sample Rate",
            value="48000",
            options=[
                ft.dropdown.Option(key=str(opt["value"]), text=opt["label"])
                for opt in SAMPLE_RATE_OPTIONS
            ],
            border_color=self.theme.color_scheme.outline,
            expand=True,
        )

        # 声道下拉框
        self._channels_dropdown = ft.Dropdown(
            label="Channels",
            value="2",
            options=[
                ft.dropdown.Option(key=str(opt["value"]), text=opt["label"])
                for opt in CHANNEL_OPTIONS
            ],
            border_color=self.theme.color_scheme.outline,
            expand=True,
        )

        # 音频滤波器开关
        self._filter_switch = ft.Switch(
            label="Enable Voice Enhancement Filter",
            value=True,
            active_color=self.theme.color_scheme.primary,
        )

        # 高通滤波频率
        self._highpass_field = ft.TextField(
            label="Highpass (Hz)",
            value="200",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=self.theme.color_scheme.outline,
            expand=True,
        )

        # 低通滤波频率
        self._lowpass_field = ft.TextField(
            label="Lowpass (Hz)",
            value="3000",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=self.theme.color_scheme.outline,
            expand=True,
        )

        # 音量
        self._volume_field = ft.TextField(
            label="Volume Multiplier",
            value="1.0",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=self.theme.color_scheme.outline,
            expand=True,
        )

        return [
            ft.Text(
                "Input",
                size=13,
                weight=ft.FontWeight.W_500,
                color=self.theme.color_scheme.on_surface,
            ),
            ft.Row(
                controls=[
                    self._input_path_field,
                    ft.IconButton(
                        icon=ft.Icons.FOLDER_OPEN,
                        tooltip="Browse",
                        on_click=lambda e: self._on_browse_click("video"),
                        icon_color=self.theme.color_scheme.primary,
                    ),
                ],
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Container(height=16),
            ft.Text(
                "Output Settings",
                size=13,
                weight=ft.FontWeight.W_500,
                color=self.theme.color_scheme.on_surface,
            ),
            self._format_dropdown,
            ft.Container(height=8),
            ft.Row(
                controls=[
                    self._sample_rate_dropdown,
                    self._channels_dropdown,
                ],
                spacing=12,
            ),
            ft.Container(height=16),
            ft.Text(
                "Audio Filter",
                size=13,
                weight=ft.FontWeight.W_500,
                color=self.theme.color_scheme.on_surface,
            ),
            self._filter_switch,
            ft.Container(height=8),
            ft.Row(
                controls=[
                    self._highpass_field,
                    self._lowpass_field,
                ],
                spacing=12,
            ),
            ft.Container(height=8),
            self._volume_field,
        ]

    def _build_transcription_config(self) -> List[ft.Control]:
        """语音转录配置

        注意：语音转写任务只做语音识别，不包含翻译步骤，
        因此不支持双语字幕选项（双语需要原文+译文）。
        """
        self._input_path_field = ft.TextField(
            label="Audio/Video File Path",
            hint_text="Enter path or click Browse to select file",
            border_color=self.theme.color_scheme.outline,
            expand=True,
        )

        # 输出格式选择
        self._output_format_type_dropdown = ft.Dropdown(
            label="Output Format",
            options=[
                ft.dropdown.Option(opt["value"], opt["label"])
                for opt in OUTPUT_FORMAT_TYPE_OPTIONS
            ],
            value="srt",
            width=200,
            border_color=self.theme.color_scheme.outline,
            on_select=self._on_transcription_output_format_change,
        )

        # ASS样式预设下拉框（仅ASS格式时显示）
        self._style_preset_dropdown = ft.Dropdown(
            label="Style Preset",
            options=[
                ft.dropdown.Option(opt["value"], opt["label"])
                for opt in ASS_STYLE_PRESETS
            ],
            value="default",
            width=200,
            visible=False,
            border_color=self.theme.color_scheme.outline,
        )

        # 语音转写任务不支持双语（没有翻译步骤），设置为 None
        self._bilingual_switch = None
        self._bilingual_layout_dropdown = None

        return [
            ft.Text(
                "Input",
                size=13,
                weight=ft.FontWeight.W_500,
                color=self.theme.color_scheme.on_surface,
            ),
            ft.Row(
                controls=[
                    self._input_path_field,
                    ft.IconButton(
                        icon=ft.Icons.FOLDER_OPEN,
                        tooltip="Browse",
                        on_click=lambda e: self._on_browse_click("audio_video"),
                        icon_color=self.theme.color_scheme.primary,
                    ),
                ],
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Container(height=16),
            ft.Text(
                "Output",
                size=13,
                weight=ft.FontWeight.W_500,
                color=self.theme.color_scheme.on_surface,
            ),
            self._output_format_type_dropdown,
            self._style_preset_dropdown,  # ASS样式预设
            ft.Container(height=16),
            ft.Text(
                "Language",
                size=13,
                weight=ft.FontWeight.W_500,
                color=self.theme.color_scheme.on_surface,
            ),
            ft.Text(
                "Auto Detect (Recommended)",
                size=13,
                color=self.theme.color_scheme.primary,
            ),
        ]

    def _on_transcription_output_format_change(self, e) -> None:
        """转录任务输出格式变更 - 仅控制ASS样式预设显示"""
        format_value = e.control.value
        is_ass = format_value == "ass"

        # 显示/隐藏样式预设（仅ASS时显示）
        if hasattr(self, "_style_preset_dropdown") and self._style_preset_dropdown:
            self._style_preset_dropdown.visible = is_ass
            try:
                self._style_preset_dropdown.update()
            except Exception:
                pass

    def _build_subtitle_translation_config(self) -> List[ft.Control]:
        """字幕翻译配置"""
        self._input_path_field = ft.TextField(
            label="SRT File Path",
            hint_text="Enter path or click Browse to select file",
            border_color=self.theme.color_scheme.outline,
            expand=True,
        )
        self._target_lang_dropdown = ft.Dropdown(
            label="To",
            options=[ft.dropdown.Option(k, v) for k, v in TARGET_LANGUAGES.items()],
            value="zh",
            width=150,
            border_color=self.theme.color_scheme.outline,
        )

        # LLM 选项
        self._use_llm_switch = ft.Switch(
            label="Use Remote LLM for translation",
            value=False,
            on_change=self._on_llm_switch_change,
            active_color=self.theme.color_scheme.primary,
        )

        llm_options = self._build_llm_dropdown_options()
        self._llm_preset_dropdown = ft.Dropdown(
            label="LLM Provider",
            options=llm_options,
            value="openai",
            width=280,
            visible=False,
            border_color=self.theme.color_scheme.outline,
        )

        return [
            ft.Text(
                "Input",
                size=13,
                weight=ft.FontWeight.W_500,
                color=self.theme.color_scheme.on_surface,
            ),
            ft.Row(
                controls=[
                    self._input_path_field,
                    ft.IconButton(
                        icon=ft.Icons.FOLDER_OPEN,
                        tooltip="Browse",
                        on_click=lambda e: self._on_browse_click("srt"),
                        icon_color=self.theme.color_scheme.primary,
                    ),
                ],
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Container(height=16),
            ft.Text(
                "Language",
                size=13,
                weight=ft.FontWeight.W_500,
                color=self.theme.color_scheme.on_surface,
            ),
            ft.Row(
                controls=[
                    ft.Text(
                        "Auto Detect →",
                        size=13,
                        color=self.theme.color_scheme.on_surface_variant,
                    ),
                    self._target_lang_dropdown,
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Container(height=16),
            ft.Text(
                "Translation",
                size=13,
                weight=ft.FontWeight.W_500,
                color=self.theme.color_scheme.on_surface,
            ),
            self._use_llm_switch,
            self._llm_preset_dropdown,
        ]

    def _build_video_enhancement_config(self) -> List[ft.Control]:
        """视频增强配置"""
        self._input_path_field = ft.TextField(
            label="Video File Path",
            hint_text="Enter path or click Browse",
            border_color=self.theme.color_scheme.outline,
            expand=True,
        )

        # 预设模式选择
        self._preset_dropdown = ft.Dropdown(
            label="Preset Mode",
            options=[
                ft.dropdown.Option(opt["value"], opt["label"])
                for opt in ENHANCEMENT_PRESET_OPTIONS
            ],
            value="fast",
            width=280,
            border_color=self.theme.color_scheme.outline,
            on_select=self._on_enhancement_preset_change,
        )

        # 放大倍数
        self._scale_dropdown = ft.Dropdown(
            label="Scale",
            options=[
                ft.dropdown.Option(str(opt["value"]), opt["label"])
                for opt in ENHANCEMENT_SCALE_OPTIONS
            ],
            value="4",
            width=200,
            border_color=self.theme.color_scheme.outline,
        )

        # 模型类型
        self._model_type_dropdown = ft.Dropdown(
            label="Model Type",
            options=[
                ft.dropdown.Option(opt["value"], opt["label"])
                for opt in ENHANCEMENT_MODEL_OPTIONS
            ],
            value="general",
            width=200,
            border_color=self.theme.color_scheme.outline,
        )

        # 高级选项 - 去噪开关
        self._denoise_switch = ft.Switch(
            label="Enable Denoising",
            value=False,
            active_color=self.theme.color_scheme.primary,
        )

        # 高级选项 - 人脸修复开关
        self._face_fix_switch = ft.Switch(
            label="Enable Face Restoration",
            value=False,
            active_color=self.theme.color_scheme.primary,
        )

        # 高级选项 - 时序平滑开关
        self._temporal_switch = ft.Switch(
            label="Enable Temporal Smoothing",
            value=False,
            active_color=self.theme.color_scheme.primary,
        )

        return [
            ft.Text(
                "Input",
                size=13,
                weight=ft.FontWeight.W_500,
                color=self.theme.color_scheme.on_surface,
            ),
            ft.Row(
                controls=[
                    self._input_path_field,
                    ft.IconButton(
                        icon=ft.Icons.FOLDER_OPEN,
                        tooltip="Browse",
                        on_click=lambda e: self._on_browse_click("video"),
                        icon_color=self.theme.color_scheme.primary,
                    ),
                ],
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Container(height=16),
            ft.Text(
                "Enhancement Settings",
                size=13,
                weight=ft.FontWeight.W_500,
                color=self.theme.color_scheme.on_surface,
            ),
            self._preset_dropdown,
            ft.Container(height=8),
            ft.Row(
                controls=[
                    self._scale_dropdown,
                    self._model_type_dropdown,
                ],
                spacing=12,
            ),
            ft.Container(height=16),
            ft.Text(
                "Advanced Options",
                size=13,
                weight=ft.FontWeight.W_500,
                color=self.theme.color_scheme.on_surface,
            ),
            self._denoise_switch,
            self._face_fix_switch,
            self._temporal_switch,
        ]

    def _on_enhancement_preset_change(self, e) -> None:
        """预设模式变更 - 自动更新高级选项"""
        preset = e.control.value

        # 根据预设自动设置高级选项
        if preset == "fast":
            self._denoise_switch.value = False
            self._face_fix_switch.value = False
            self._temporal_switch.value = False
        elif preset == "balanced":
            self._denoise_switch.value = True
            self._face_fix_switch.value = True
            self._temporal_switch.value = False
        elif preset == "quality":
            self._denoise_switch.value = True
            self._face_fix_switch.value = True
            self._temporal_switch.value = True

        # 更新UI
        try:
            self._denoise_switch.update()
            self._face_fix_switch.update()
            self._temporal_switch.update()
        except Exception:
            pass

    def _build_actions(self) -> List[ft.Control]:
        """构建操作按钮"""
        if self._step == 1:
            return [
                ft.TextButton("Cancel", on_click=lambda e: self._on_cancel_click()),
            ]
        else:
            return [
                ft.TextButton("Cancel", on_click=lambda e: self._on_cancel_click()),
                ft.ElevatedButton(
                    "Add Task",
                    icon=ft.Icons.ADD,
                    on_click=lambda e: self._on_confirm_click(),
                    bgcolor=self.theme.color_scheme.primary,
                    color=self.theme.color_scheme.on_primary,
                ),
            ]

    def _update_content(self) -> None:
        """更新对话框内容"""
        self._rebuild_and_show()

    def _on_type_select(self, type_id: str) -> None:
        """选择任务类型"""
        from mediafactory.logging import log_info

        log_info(f"Task type selected: {type_id}")
        self._selected_type = type_id
        self._step = 2  # 切换到步骤2：配置参数
        self._update_content()

    def _go_back(self) -> None:
        """返回上一步"""
        self._step = 1
        self._update_content()

    def _on_confirm_click(self) -> None:
        """确认添加任务"""
        config = self._collect_config()
        if config:
            self.close()
            if self.on_confirm:
                self.on_confirm(config)

    def _on_cancel_click(self) -> None:
        """取消"""
        from mediafactory.logging import log_info

        log_info("Cancel button clicked")
        self.close()
        if self.on_cancel:
            self.on_cancel()

    def _on_dismiss(self) -> None:
        """对话框关闭"""
        pass

    def _build_llm_dropdown_options(self) -> List[ft.dropdown.Option]:
        """构建带信号点的 LLM 下拉框选项"""
        config = get_config()
        options = []

        for preset_id, preset_info in BackendConfigMapping.BASE_URL_PRESETS.items():
            if preset_id == "custom":
                continue

            # 从配置中获取连通性状态
            preset_config = config.openai_compatible.get_preset_config(preset_id)
            available = preset_config.connection_available

            # 使用 emoji 圆点作为信号指示器
            dot_icon = "🟢" if available else "🔴"

            options.append(
                ft.dropdown.Option(
                    key=preset_id,
                    text=f"{dot_icon} {preset_info['display_name']}",
                )
            )

        return options

    def _on_llm_switch_change(self, e) -> None:
        """LLM 开关变更 - 显示/隐藏下拉框"""
        if hasattr(self, "_llm_preset_dropdown") and self._llm_preset_dropdown:
            self._llm_preset_dropdown.visible = e.control.value
            try:
                self._llm_preset_dropdown.update()
            except Exception:
                pass

    def _on_bilingual_switch_change(self, e) -> None:
        """双语开关变更 - 显示/隐藏布局下拉框"""
        if (
            hasattr(self, "_bilingual_layout_dropdown")
            and self._bilingual_layout_dropdown
        ):
            self._bilingual_layout_dropdown.visible = e.control.value
            try:
                self._bilingual_layout_dropdown.update()
            except Exception:
                pass

    def _on_output_format_change(self, e) -> None:
        """输出格式变更 - 根据格式显示/隐藏双语选项和样式预设"""
        format_value = e.control.value
        is_subtitle_format = format_value in ("srt", "ass")  # SRT和ASS都支持双语
        is_ass = format_value == "ass"

        # 显示/隐藏样式预设（仅ASS时显示）
        if hasattr(self, "_style_preset_dropdown") and self._style_preset_dropdown:
            self._style_preset_dropdown.visible = is_ass
            try:
                self._style_preset_dropdown.update()
            except Exception:
                pass

        # 显示/隐藏双语开关（SRT和ASS时显示）
        if hasattr(self, "_bilingual_switch") and self._bilingual_switch:
            self._bilingual_switch.visible = is_subtitle_format
            if not is_subtitle_format:
                self._bilingual_switch.value = False
            try:
                self._bilingual_switch.update()
            except Exception:
                pass

        # 隐藏布局下拉框
        if (
            hasattr(self, "_bilingual_layout_dropdown")
            and self._bilingual_layout_dropdown
        ):
            self._bilingual_layout_dropdown.visible = (
                is_subtitle_format and self._bilingual_switch.value
            )
            try:
                self._bilingual_layout_dropdown.update()
            except Exception:
                pass

    def _on_browse_click(self, filter_type: str) -> None:
        """Browse 按钮点击处理"""
        from mediafactory.logging import log_info, log_error

        if not self._selected_type:
            log_info("Browse clicked but no task type selected")
            return

        filter_config = FILE_FILTERS.get(filter_type, FILE_FILTERS["video"])
        log_info(f"Opening file picker for task type: {self._selected_type}")

        # Flet 0.80+ 新用法：直接创建 FilePicker 实例并 await pick_files()
        # 不需要添加到 page.overlay
        async def pick_files_async():
            try:
                # 每次创建新的 FilePicker 实例
                files = await ft.FilePicker().pick_files(
                    dialog_title=filter_config["dialog_title"],
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=filter_config["extensions"],
                    allow_multiple=False,
                )

                log_info(f"File picker result: files={files}")

                if files and len(files) > 0:
                    selected_path = files[0].path
                    log_info(f"Selected file path: {selected_path}")

                    if hasattr(self, "_input_path_field") and self._input_path_field:
                        self._input_path_field.value = selected_path
                        try:
                            self._input_path_field.update()
                            log_info("Input field updated successfully")
                        except Exception as ex:
                            log_error(f"Failed to update input field: {ex}")
                else:
                    log_info("No file selected")
            except Exception as ex:
                log_error(f"File picker error: {ex}")

        self.page.run_task(pick_files_async)

    def _collect_config(self) -> Optional[TaskConfig]:
        """收集配置"""
        input_path = ""
        source_lang = "auto"
        target_lang = "zh"
        output_format = "wav"
        output_format_type = "srt"
        use_llm = False
        llm_preset = "openai"
        # 音频参数默认值（最高质量）
        sample_rate = 48000
        channels = 2
        filter_enabled = True
        highpass_freq = 200
        lowpass_freq = 3000
        volume = 1.0

        if hasattr(self, "_input_path_field") and self._input_path_field:
            input_path = self._input_path_field.value or ""

        if hasattr(self, "_target_lang_dropdown") and self._target_lang_dropdown:
            target_lang = self._target_lang_dropdown.value or "zh"

        if hasattr(self, "_source_lang_dropdown") and self._source_lang_dropdown:
            source_lang = self._source_lang_dropdown.value or "auto"

        if hasattr(self, "_format_dropdown") and self._format_dropdown:
            output_format = self._format_dropdown.value or "wav"

        # 收集输出格式类型
        if (
            hasattr(self, "_output_format_type_dropdown")
            and self._output_format_type_dropdown
        ):
            output_format_type = self._output_format_type_dropdown.value or "srt"

        # 收集音频参数
        if hasattr(self, "_sample_rate_dropdown") and self._sample_rate_dropdown:
            sample_rate = int(self._sample_rate_dropdown.value or "48000")

        if hasattr(self, "_channels_dropdown") and self._channels_dropdown:
            channels = int(self._channels_dropdown.value or "2")

        if hasattr(self, "_filter_switch") and self._filter_switch:
            filter_enabled = self._filter_switch.value

        if hasattr(self, "_highpass_field") and self._highpass_field:
            try:
                highpass_freq = int(self._highpass_field.value or "200")
                highpass_freq = max(20, min(500, highpass_freq))
            except ValueError:
                highpass_freq = 200

        if hasattr(self, "_lowpass_field") and self._lowpass_field:
            try:
                lowpass_freq = int(self._lowpass_field.value or "3000")
                lowpass_freq = max(1000, min(16000, lowpass_freq))
            except ValueError:
                lowpass_freq = 3000

        if hasattr(self, "_volume_field") and self._volume_field:
            try:
                volume = float(self._volume_field.value or "1.0")
                volume = max(0.1, min(2.0, volume))
            except ValueError:
                volume = 1.0

        # 收集 LLM 配置
        if hasattr(self, "_use_llm_switch") and self._use_llm_switch:
            use_llm = self._use_llm_switch.value

        if hasattr(self, "_llm_preset_dropdown") and self._llm_preset_dropdown:
            llm_preset = self._llm_preset_dropdown.value or "openai"

        # 收集双语字幕配置
        bilingual = False
        bilingual_layout = "translate_on_top"
        if hasattr(self, "_bilingual_switch") and self._bilingual_switch is not None:
            bilingual = self._bilingual_switch.value
        if (
            hasattr(self, "_bilingual_layout_dropdown")
            and self._bilingual_layout_dropdown is not None
        ):
            bilingual_layout = (
                self._bilingual_layout_dropdown.value or "translate_on_top"
            )

        # 收集ASS样式预设
        style_preset = "default"
        if hasattr(self, "_style_preset_dropdown") and self._style_preset_dropdown:
            style_preset = self._style_preset_dropdown.value or "default"

        # 收集视频增强配置
        enhancement_preset = "fast"
        enhancement_scale = 4
        enhancement_model = "general"
        enhancement_denoise = False
        enhancement_face_fix = False
        enhancement_temporal = False

        if hasattr(self, "_preset_dropdown") and self._preset_dropdown:
            enhancement_preset = self._preset_dropdown.value or "fast"

        if hasattr(self, "_scale_dropdown") and self._scale_dropdown:
            try:
                enhancement_scale = int(self._scale_dropdown.value or "4")
            except ValueError:
                enhancement_scale = 4

        if hasattr(self, "_model_type_dropdown") and self._model_type_dropdown:
            enhancement_model = self._model_type_dropdown.value or "general"

        if hasattr(self, "_denoise_switch") and self._denoise_switch:
            enhancement_denoise = self._denoise_switch.value

        if hasattr(self, "_face_fix_switch") and self._face_fix_switch:
            enhancement_face_fix = self._face_fix_switch.value

        if hasattr(self, "_temporal_switch") and self._temporal_switch:
            enhancement_temporal = self._temporal_switch.value

        # 验证必填项
        if not input_path:
            return None

        return TaskConfig(
            task_type=self._selected_type or "subtitle",
            input_path=input_path,
            source_lang=source_lang,
            target_lang=target_lang,
            use_llm=use_llm,
            llm_preset=llm_preset,
            output_format=output_format,
            sample_rate=sample_rate,
            channels=channels,
            filter_enabled=filter_enabled,
            highpass_freq=highpass_freq,
            lowpass_freq=lowpass_freq,
            volume=volume,
            output_format_type=output_format_type,
            bilingual=bilingual,
            bilingual_layout=bilingual_layout,
            style_preset=style_preset,
            enhancement_preset=enhancement_preset,
            enhancement_scale=enhancement_scale,
            enhancement_model=enhancement_model,
            enhancement_denoise=enhancement_denoise,
            enhancement_face_fix=enhancement_face_fix,
            enhancement_temporal=enhancement_temporal,
        )
