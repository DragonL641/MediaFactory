"""资源清理协议模块

定义统一的资源清理接口，确保所有持有大资源的组件都能正确释放资源。
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ResourceCleanupProtocol(Protocol):
    """资源清理协议

    所有持有需要释放的资源（如模型、连接、线程）的组件都应实现此协议。
    使用 Protocol 实现结构化子类型，无需显式继承。

    Example:
        ```python
        class TranslationEngine:
            def cleanup(self) -> None:
                # 释放资源
                self._model = None
                gc.collect()
        ```

        # 类型检查
        engine = TranslationEngine()
        if isinstance(engine, ResourceCleanupProtocol):
            engine.cleanup()
    """

    def cleanup(self) -> None:
        """释放资源

        实现此方法以释放组件持有的所有资源。
        应该：
        - 删除大对象的引用（设置为 None）
        - 调用 gc.collect() 触发垃圾回收
        - 如果使用 CUDA，调用 torch.cuda.empty_cache()
        - 关闭连接、文件句柄等

        注意：
        - 此方法应该是幂等的（多次调用不会出错）
        - 此方法不应该抛出异常
        """
        ...
