"""
Material Design 3 主题系统

定义应用的视觉风格，包括颜色、字体、圆角等。
"""

import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable

import flet as ft


class ThemeMode(Enum):
    """主题模式"""

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


@dataclass
class ColorScheme:
    """颜色方案 - 基于 Material Design 3"""

    # 主色调 (Indigo)
    primary: str = "#6750A4"
    on_primary: str = "#FFFFFF"
    primary_container: str = "#EADDFF"
    on_primary_container: str = "#21005D"

    # 次要色调
    secondary: str = "#625B71"
    on_secondary: str = "#FFFFFF"
    secondary_container: str = "#E8DEF8"
    on_secondary_container: str = "#1D192B"

    # 第三色调
    tertiary: str = "#7D5260"
    on_tertiary: str = "#FFFFFF"
    tertiary_container: str = "#FFD8E4"
    on_tertiary_container: str = "#31111D"

    # 错误色
    error: str = "#B3261E"
    on_error: str = "#FFFFFF"
    error_container: str = "#F9DEDC"
    on_error_container: str = "#410E0B"

    # 背景色 (亮色模式默认值)
    surface: str = "#FFFBFE"
    on_surface: str = "#1C1B1F"
    surface_variant: str = "#E7E0EC"
    on_surface_variant: str = "#49454F"

    # 轮廓色
    outline: str = "#79747E"
    outline_variant: str = "#CAC4D0"

    # 其他
    shadow: str = "#000000"
    scrim: str = "#000000"
    inverse_surface: str = "#313033"
    inverse_on_surface: str = "#F4EFF4"
    inverse_primary: str = "#D0BCFF"


@dataclass
class DarkColorScheme(ColorScheme):
    """暗色模式颜色方案"""

    primary: str = "#D0BCFF"
    on_primary: str = "#381E72"
    primary_container: str = "#4F378B"
    on_primary_container: str = "#EADDFF"

    secondary: str = "#CCC2DC"
    on_secondary: str = "#332D41"
    secondary_container: str = "#4A4458"
    on_secondary_container: str = "#E8DEF8"

    tertiary: str = "#EFB8C8"
    on_tertiary: str = "#492532"
    tertiary_container: str = "#633B48"
    on_tertiary_container: str = "#FFD8E4"

    error: str = "#F2B8B5"
    on_error: str = "#601410"
    error_container: str = "#8C1D18"
    on_error_container: str = "#F9DEDC"

    surface: str = "#1C1B1F"
    on_surface: str = "#E6E1E5"
    surface_variant: str = "#49454F"
    on_surface_variant: str = "#CAC4D0"

    outline: str = "#938F99"
    outline_variant: str = "#49454F"

    shadow: str = "#000000"
    scrim: str = "#000000"
    inverse_surface: str = "#E6E1E5"
    inverse_on_surface: str = "#313033"
    inverse_primary: str = "#6750A4"


@dataclass
class AppTheme:
    """应用主题配置"""

    mode: ThemeMode = ThemeMode.SYSTEM
    color_scheme: ColorScheme = field(default_factory=ColorScheme)

    # 字体设置
    font_family: str = "system-ui"
    font_size_xs: int = 10
    font_size_sm: int = 12
    font_size_base: int = 14
    font_size_lg: int = 16
    font_size_xl: int = 20
    font_size_2xl: int = 24
    font_size_3xl: int = 32

    # 间距
    spacing_xs: int = 4
    spacing_sm: int = 8
    spacing_md: int = 16
    spacing_lg: int = 24
    spacing_xl: int = 32

    # 圆角
    radius_sm: int = 4
    radius_md: int = 8
    radius_lg: int = 12
    radius_xl: int = 16
    radius_full: int = 9999

    # 动画时长 (毫秒)
    animation_fast: int = 150
    animation_normal: int = 300
    animation_slow: int = 500

    # 阴影
    elevation_sm: int = 1
    elevation_md: int = 3
    elevation_lg: int = 6

    def to_flet_theme(self, page: ft.Page) -> ft.Theme:
        """转换为 Flet 主题对象"""
        is_dark = self._is_dark_mode(page)

        if is_dark:
            colors = DarkColorScheme()
        else:
            colors = self.color_scheme

        theme = ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=colors.primary,
                on_primary=colors.on_primary,
                primary_container=colors.primary_container,
                on_primary_container=colors.on_primary_container,
                secondary=colors.secondary,
                on_secondary=colors.on_secondary,
                secondary_container=colors.secondary_container,
                on_secondary_container=colors.on_secondary_container,
                tertiary=colors.tertiary,
                on_tertiary=colors.on_tertiary,
                tertiary_container=colors.tertiary_container,
                on_tertiary_container=colors.on_tertiary_container,
                error=colors.error,
                on_error=colors.on_error,
                error_container=colors.error_container,
                on_error_container=colors.on_error_container,
                surface=colors.surface,
                on_surface=colors.on_surface,
                surface_container=colors.surface_variant,
                on_surface_variant=colors.on_surface_variant,
                outline=colors.outline,
                outline_variant=colors.outline_variant,
                shadow=colors.shadow,
                scrim=colors.scrim,
                inverse_surface=colors.inverse_surface,
                on_inverse_surface=colors.inverse_on_surface,
                inverse_primary=colors.inverse_primary,
            ),
            font_family=self.font_family,
        )

        # 使用 Material Design 3
        theme.use_material3 = True

        return theme

    def _is_dark_mode(self, page: ft.Page) -> bool:
        """判断是否为暗色模式"""
        if self.mode == ThemeMode.DARK:
            return True
        elif self.mode == ThemeMode.LIGHT:
            return False
        else:  # SYSTEM
            return page.platform_brightness == ft.ThemeMode.DARK


# ==================== 语义颜色 ====================

# 语义颜色常量 - 用于状态指示（成功、警告、错误等）
SEMANTIC_COLORS = {
    "success": "#4CAF50",
    "warning": "#FF9800",
    "error": "#F44336",
}


# ==================== 单例管理 ====================

# 全局主题实例和锁
_theme_instance: Optional[AppTheme] = None
_theme_lock = threading.Lock()


def get_theme() -> AppTheme:
    """获取全局主题实例（线程安全）"""
    global _theme_instance
    if _theme_instance is None:
        with _theme_lock:
            if _theme_instance is None:
                _theme_instance = AppTheme()
    return _theme_instance


def reset_theme() -> None:
    """重置全局主题实例（用于测试）"""
    global _theme_instance
    with _theme_lock:
        _theme_instance = None


def set_theme_mode(mode: ThemeMode) -> None:
    """设置主题模式"""
    theme = get_theme()
    theme.mode = mode


def apply_theme(page: ft.Page) -> None:
    """应用主题到页面"""
    theme = get_theme()
    page.theme = theme.to_flet_theme(page)
    page.dark_theme = theme.to_flet_theme(page)

    # 设置页面主题模式
    if theme.mode == ThemeMode.DARK:
        page.theme_mode = ft.ThemeMode.DARK
    elif theme.mode == ThemeMode.LIGHT:
        page.theme_mode = ft.ThemeMode.LIGHT
    else:
        page.theme_mode = ft.ThemeMode.SYSTEM

    page.update()
