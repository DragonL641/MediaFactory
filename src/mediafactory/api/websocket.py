"""
WebSocket 连接管理器

管理 WebSocket 连接和消息广播。
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self._active_connections: Set[WebSocket] = set()
        self._task_subscriptions: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        """接受新连接"""
        await websocket.accept()
        async with self._lock:
            self._active_connections.add(websocket)
        logger.debug(f"WebSocket connected. Total: {len(self._active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        self._active_connections.discard(websocket)
        # 清理订阅
        for task_id in list(self._task_subscriptions.keys()):
            self._task_subscriptions[task_id].discard(websocket)
            if not self._task_subscriptions[task_id]:
                del self._task_subscriptions[task_id]
        logger.debug(f"WebSocket disconnected. Total: {len(self._active_connections)}")

    async def subscribe(self, websocket: WebSocket, task_id: str):
        """订阅任务进度"""
        async with self._lock:
            if task_id not in self._task_subscriptions:
                self._task_subscriptions[task_id] = set()
            self._task_subscriptions[task_id].add(websocket)
        logger.debug(f"WebSocket subscribed to task {task_id}")

    async def unsubscribe(self, websocket: WebSocket, task_id: str):
        """取消订阅"""
        async with self._lock:
            if task_id in self._task_subscriptions:
                self._task_subscriptions[task_id].discard(websocket)
                if not self._task_subscriptions[task_id]:
                    del self._task_subscriptions[task_id]

    async def handle_message(self, websocket: WebSocket, data: Dict[str, Any]):
        """处理客户端消息"""
        msg_type = data.get("type")

        if msg_type == "subscribe":
            task_id = data.get("task_id")
            if task_id:
                await self.subscribe(websocket, task_id)
                await websocket.send_json(
                    {"type": "subscribed", "task_id": task_id}
                )
        elif msg_type == "unsubscribe":
            task_id = data.get("task_id")
            if task_id:
                await self.unsubscribe(websocket, task_id)
        else:
            logger.warning(f"Unknown WebSocket message type: {msg_type}")

    async def broadcast_progress(
        self,
        task_id: str,
        status: str,
        progress: float,
        message: str = "",
        stage: Optional[str] = None,
        **extra: Any,
    ):
        """广播任务进度（发送给所有连接）"""
        data = {
            "type": "progress",
            "task_id": task_id,
            "data": {
                "status": status,
                "progress": progress,
                "message": message,
                "stage": stage,
                **extra,
            },
        }
        await self.broadcast(data)

    async def broadcast_task_complete(
        self,
        task_id: str,
        success: bool,
        output_path: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """广播任务完成（发送给所有连接）"""
        data = {
            "type": "task_complete",
            "task_id": task_id,
            "data": {
                "success": success,
                "output_path": output_path,
                "error": error,
            },
        }
        await self.broadcast(data)

    async def broadcast(self, message: Dict[str, Any]):
        """广播消息给所有连接"""
        dead_connections = set()
        for connection in self._active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to broadcast: {e}")
                dead_connections.add(connection)

        for conn in dead_connections:
            self.disconnect(conn)


# 全局管理器实例
manager = ConnectionManager()
