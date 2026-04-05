"""
MediaFactory FastAPI Backend

为 Electron 前端提供 HTTP + WebSocket API。
"""

from mediafactory.api.main import create_app, get_app

__all__ = ["create_app", "get_app"]
