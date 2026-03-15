"""
MediaFactory Flet 应用入口

使用横向页签导航布局。
"""

from typing import Optional, Callable, Dict, Any
import threading
import flet as ft

from mediafactory.logging import log_info, log_error, setup_app_logging
from mediafactory.gui.flet.theme import get_theme
from mediafactory.gui.flet.components.navigation import TopNavigation, NAV_ITEMS


class AppInitializer:
    """应用启动初始化器 - 集中管理所有启动任务"""

    def __init__(self):
        self._initialized = False

    def initialize(self) -> None:
        """执行所有初始化任务（在后台线程中）"""
        if self._initialized:
            return

        def run_initialization():
            # 1. 同步模型列表
            self._sync_models()

            # 2. 测试 LLM 连通性
            self._test_llm_connections()

            self._initialized = True
            log_info("应用初始化完成")

        thread = threading.Thread(target=run_initialization, daemon=True)
        thread.start()

    def _sync_models(self) -> None:
        """同步模型列表"""
        try:
            from mediafactory.config import get_config_manager

            config_manager = get_config_manager()
            config_manager.sync_models()
            log_info("模型同步完成")
        except Exception as e:
            log_error(f"模型同步失败: {e}")

    def _test_llm_connections(self) -> None:
        """测试所有 LLM 连通性并更新配置文件"""
        try:
            from mediafactory.gui.flet.services import get_model_status_service
            from mediafactory.config import update_config

            service = get_model_status_service()

            # 直接调用同步方法
            results = service.test_all_llm_connections()

            # 更新配置文件中的 connection_available 字段
            for preset_id, result in results.items():
                try:
                    update_config(
                        **{
                            f"openai_compatible__{preset_id}__connection_available": result.get(
                                "success", False
                            )
                        }
                    )
                except Exception as e:
                    log_error(f"更新 {preset_id} 连接状态失败: {e}")

            log_info("LLM 连通性测试完成")
        except Exception as e:
            log_error(f"LLM 连通性测试失败: {e}")


class MediaFactoryApp:
    """MediaFactory Flet 应用"""

    # 路由到页面ID的映射
    ROUTE_TO_PAGE = {
        "/tasks": "tasks",
        "/models": "models",
        "/llm-config": "llm_config",
    }

    PAGE_TO_ROUTE = {v: k for k, v in ROUTE_TO_PAGE.items()}

    def __init__(self, page: ft.Page):
        self.page = page
        self._navigation: Optional[TopNavigation] = None
        self._content_area: Optional[ft.Container] = None
        self._current_page: str = "tasks"

        # 页面构建器缓存
        self._page_builders: Dict[str, Callable] = {}

        # 初始化页面
        self._setup_page()

        # 加载页面构建器
        self._load_page_builders()

        # 构建UI
        self._build_ui()

        # 启动应用初始化（后台执行）
        AppInitializer().initialize()

    def _setup_page(self) -> None:
        """设置页面基础配置"""
        self.page.title = "MediaFactory"
        self.page.window.width = 1100
        self.page.window.height = 750
        self.page.window.min_width = 900
        self.page.window.min_height = 600

        # 设置窗口图标（跨平台）
        from .resources import get_icon_path

        icon_path = get_icon_path()
        if icon_path:
            self.page.window.icon = str(icon_path)
            self.page.update()

        # 固定使用 Light 主题
        self.page.theme_mode = ft.ThemeMode.LIGHT

        # 窗口关闭事件
        self.page.window.on_event = self._on_window_event

        log_info("Flet 应用页面初始化完成")

    def _load_page_builders(self) -> None:
        """加载页面构建器"""
        # 延迟导入以避免循环依赖
        from mediafactory.gui.flet.pages.tasks import build_tasks_page
        from mediafactory.gui.flet.pages.models import build_models_page
        from mediafactory.gui.flet.pages.llm_config import build_llm_config_page

        self._page_builders = {
            "tasks": build_tasks_page,
            "models": build_models_page,
            "llm_config": build_llm_config_page,
        }

        log_info("页面构建器加载完成")

    def _build_ui(self) -> None:
        """构建UI"""
        theme = get_theme()

        # 创建导航栏
        self._navigation = TopNavigation(
            on_navigate=self._on_navigate,
            current_page=self._current_page,
        )

        # 创建内容区域
        self._content_area = ft.Container(
            content=self._build_page_content(self._current_page),
            expand=True,
            padding=ft.padding.all(20),
            bgcolor=theme.color_scheme.surface_variant,
        )

        # 主布局：标题区域 → 导航栏 → 内容区域
        main_layout = ft.Column(
            controls=[
                # 应用标题区域
                self._build_app_header(),
                # 导航栏
                self._navigation.build(),
                # 内容区域
                self._content_area,
            ],
            spacing=0,
            expand=True,
        )

        # 清除现有内容并添加新布局
        self.page.clean()
        self.page.add(main_layout)
        self.page.update()

        log_info(f"UI构建完成，当前页面: {self._current_page}")

    def _build_app_header(self) -> ft.Control:
        """构建应用标题区域"""
        theme = get_theme()

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.VIDEO_LIBRARY,
                        size=28,
                        color=theme.color_scheme.primary,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(
                                "MediaFactory",
                                size=20,
                                weight=ft.FontWeight.BOLD,
                                color=theme.color_scheme.on_surface,
                            ),
                            ft.Text(
                                "Version 3.2.0 | Multimedia Processing Platform",
                                size=11,
                                color=theme.color_scheme.on_surface_variant,
                            ),
                        ],
                        spacing=2,
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=20, vertical=12),
            bgcolor=theme.color_scheme.surface,
        )

    def _build_page_content(self, page_id: str) -> ft.Control:
        """构建页面内容"""
        builder = self._page_builders.get(page_id)
        if builder:
            return builder(self.page, {})

        # 默认返回空白页面
        theme = get_theme()
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(
                        ft.Icons.ERROR_OUTLINE, size=48, color=theme.color_scheme.error
                    ),
                    ft.Text(
                        f"Page not found: {page_id}",
                        size=16,
                        color=theme.color_scheme.on_surface,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                expand=True,
            ),
            expand=True,
        )

    def _on_navigate(self, page_id: str) -> None:
        """导航回调"""
        if page_id == self._current_page:
            return

        log_info(f"导航到页面: {page_id}")
        self._current_page = page_id

        # 更新导航栏选中状态
        self._navigation.set_current_page(page_id)

        # 更新内容区域
        self._content_area.content = self._build_page_content(page_id)
        self._content_area.update()

        # 更新页面标题
        page_title = next(
            (item["label"] for item in NAV_ITEMS if item["id"] == page_id),
            "MediaFactory",
        )
        self.page.title = f"MediaFactory - {page_title}"

    def _on_window_event(self, e) -> None:
        """窗口事件处理"""
        if e.data == "close":
            log_info("应用关闭")
            self.page.window.destroy()

    def run(self, initial_route: str = "/tasks") -> None:
        """运行应用"""
        # 解析初始路由
        initial_page = self.ROUTE_TO_PAGE.get(initial_route, "tasks")
        self._current_page = initial_page

        # 更新导航栏状态
        self._navigation.set_current_page(initial_page)

        # 更新内容区域
        self._content_area.content = self._build_page_content(initial_page)
        self._content_area.update()

        log_info(f"应用启动，初始页面: {initial_page}")


def create_app() -> Callable[[ft.Page], None]:
    """创建应用工厂函数"""

    def main(page: ft.Page) -> None:
        app = MediaFactoryApp(page)
        app.run()

    return main


def launch_gui() -> None:
    """启动 GUI 应用"""
    # 初始化日志
    setup_app_logging()

    log_info("启动 MediaFactory Flet GUI")

    ft.run(
        main=create_app(),
        view=ft.AppView.FLET_APP,
    )


if __name__ == "__main__":
    launch_gui()
