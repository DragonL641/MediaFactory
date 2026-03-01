"""
MediaFactory GUI Package

基于 Flet 框架的现代化 GUI，采用 Material Design 3 设计语言。
"""

from mediafactory.gui.flet import (
    launch_gui,
    MediaFactoryApp,
    get_theme,
    get_state,
)

__all__ = [
    "launch_gui",
    "MediaFactoryApp",
    "get_theme",
    "get_state",
]
