"""进度回调协议模块

将引擎层与 GUI 特定概念解耦的中性接口。
"""

from typing import Protocol


class ProgressCallback(Protocol):
    """进度回调协议"""

    def update(self, progress: float, message: str = "") -> None:
        """更新进度

        Args:
            progress: 进度值 (0-100)
            message: 进度消息
        """

    def is_cancelled(self) -> bool:
        """检查是否已取消"""
        return False


class NoOpProgressCallback:
    """空操作进度回调（用于不需要进度报告的场景）"""

    def update(self, progress: float, message: str = "") -> None:
        pass

    def is_cancelled(self) -> bool:
        return False


# 共享的空操作实例
NO_OP_PROGRESS = NoOpProgressCallback()
