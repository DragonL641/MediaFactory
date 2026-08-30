"""uvicorn Server 实例引用

供 POST /api/system/shutdown 触发优雅停机（should_exit → lifespan 收尾）。
入口（__main__ / start_server）构造 Server 后调用 set_server 注册。
"""

from __future__ import annotations

from typing import Any, Optional

# uvicorn.Server 实例；类型用 Any（避免为类型标注导入 uvicorn 产生耦合）
_server: Optional[Any] = None


def set_server(server: Any) -> None:
    """注册当前 uvicorn Server 实例（入口启动时调用一次）"""
    global _server
    _server = server


def request_shutdown() -> bool:
    """请求优雅停机。返回 False 表示 Server 未注册（如 reload 开发模式）。"""
    if _server is None:
        return False
    _server.should_exit = True
    return True
