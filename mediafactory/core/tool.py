"""取消令牌模块

简化的 CancellationToken，直接包装 threading.Event。
"""

import threading


class CancellationToken:
    """线程安全的协作式取消令牌

    简化实现：直接包装 threading.Event，同时保留取消原因功能。
    """

    def __init__(self) -> None:
        self._event = threading.Event()
        self._reason = ""
        self._lock = threading.Lock()

    def cancel(self, reason: str = "") -> None:
        """请求取消"""
        with self._lock:
            self._reason = reason
        self._event.set()

    def is_cancelled(self) -> bool:
        """检查是否已取消"""
        return self._event.is_set()

    def get_reason(self) -> str:
        """获取取消原因"""
        with self._lock:
            return self._reason

    def reset(self) -> None:
        """重置为未取消状态"""
        with self._lock:
            self._reason = ""
        self._event.clear()

    # threading.Event 兼容接口
    def set(self) -> None:
        """设置取消标志（兼容 threading.Event）"""
        self.cancel("Cancellation requested via set()")

    def clear(self) -> None:
        """清除取消标志（兼容 threading.Event）"""
        self.reset()

    def is_set(self) -> bool:
        """检查取消标志（兼容 threading.Event）"""
        return self.is_cancelled()

    def wait(self, timeout: float | None = None) -> bool:
        """等待取消标志被设置（兼容 threading.Event）"""
        return self._event.wait(timeout)
