"""
MediaFactory Flet GUI 模块

基于 Flet 框架的现代化 GUI 实现，采用 Material Design 3 设计语言。

使用方法：
    from mediafactory.gui.flet import launch_gui
    launch_gui()

或在命令行：
    mediafactory-app
"""

# 应用入口
from mediafactory.gui.flet.app import (
    MediaFactoryApp,
    create_app,
    launch_gui,
)

# 主题
from mediafactory.gui.flet.theme import (
    AppTheme,
    get_theme,
    set_theme_mode,
    apply_theme,
    ThemeMode,
)

# 状态管理
from mediafactory.gui.flet.state import (
    AppState,
    get_state,
    reset_state,
    TaskItem,
    TaskStatus,
    TaskConfig,
    ModelStatus,
)

# 路由
from mediafactory.gui.flet.router import (
    Route,
    get_route_by_path,
    get_all_routes,
)

# 服务
from mediafactory.gui.flet.services import (
    SubtitleService,
    AudioService,
    TranscriptionService,
    TranslationService,
    ModelStatusService,
    get_subtitle_service,
    get_audio_service,
    get_transcription_service,
    get_translation_service,
    get_model_status_service,
    ProcessingProgress,
    ProcessingResult,
)

# 组件
from mediafactory.gui.flet.components import (
    StatusBanner,
    BannerType,
    Sidebar,
    TaskCard,
    TaskConfigDialog,
    TASK_TYPES,
)
# ModelStatusCard 和 ModelStatusSection 已移至 Models 页面

# 页面构建器
from mediafactory.gui.flet.pages import (
    build_tasks_page,
)

__all__ = [
    # 应用
    "MediaFactoryApp",
    "create_app",
    "launch_gui",
    # 主题
    "AppTheme",
    "get_theme",
    "set_theme_mode",
    "apply_theme",
    "ThemeMode",
    # 状态
    "AppState",
    "get_state",
    "reset_state",
    "TaskItem",
    "TaskStatus",
    "TaskConfig",
    "ModelStatus",
    # 路由
    "Route",
    "get_route_by_path",
    "get_all_routes",
    # 服务
    "SubtitleService",
    "AudioService",
    "TranscriptionService",
    "TranslationService",
    "ModelStatusService",
    "get_subtitle_service",
    "get_audio_service",
    "get_transcription_service",
    "get_translation_service",
    "get_model_status_service",
    "ProcessingProgress",
    "ProcessingResult",
    # 组件
    "StatusBanner",
    "BannerType",
    "Sidebar",
    "TaskCard",
    "TaskConfigDialog",
    "TASK_TYPES",
    # 页面
    "build_tasks_page",
]

# 从主模块导入版本号（单一真相源）
from mediafactory._version import __version__
