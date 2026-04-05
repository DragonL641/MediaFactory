"""流水线上下文模块"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from ..core.progress_protocol import ProgressCallback


@dataclass
class ProcessingContext:
    """流水线处理上下文，承载所有输入、中间结果和配置"""

    # 输入
    video_path: Optional[str] = None

    # 中间结果（由各阶段填充）
    audio_path: Optional[str] = None
    transcription_result: Optional[Dict[str, Any]] = None
    translation_result: Optional[Dict[str, Any]] = None
    output_path: Optional[str] = None

    # 语言设置
    src_lang: Optional[str] = None
    tgt_lang: str = "zh"
    detected_lang: Optional[str] = None

    # 模型配置
    whisper_model: str = "auto"  # 固定使用 Large V3，"auto" 触发自动设置
    whisper_device: str = "auto"  # 自动检测最佳设备 (cuda/cpu)
    whisper_model_instance: Any = None

    translation_model: Optional[str] = None
    use_local_models_only: bool = False
    llm_backend: Any = None

    # 进度回调
    progress_callback: Optional["ProgressCallback"] = None
    gui_observers: Optional[Dict[str, Any]] = None
    config: Dict[str, Any] = field(default_factory=dict)

    # 双语字幕配置
    bilingual: bool = False
    bilingual_layout: str = "translate_on_top"

    # ASS字幕样式配置
    style_preset: str = "default"

    # 阶段跟踪
    _current_stage_name: str = "model_loading"

    def is_cancelled(self) -> bool:
        """检查是否已取消"""
        if self.progress_callback:
            return self.progress_callback.is_cancelled()
        if self.gui_observers and "cancelled" in self.gui_observers:
            return self.gui_observers["cancelled"]()
        return False

    def update_progress(self, stage: str, progress: float, message: str = ""):
        """更新进度"""
        self.set_stage(stage)
        if self.progress_callback:
            self.progress_callback.update(progress, message)
        elif self.gui_observers:
            callback_key = f"{stage}_progress_func"
            if callback_key in self.gui_observers:
                self.gui_observers[callback_key](progress, message)

    def set_stage(self, stage: str) -> None:
        """设置当前阶段"""
        self._current_stage_name = stage
        if self.progress_callback and hasattr(self.progress_callback, "set_stage"):
            try:
                self.progress_callback.set_stage(stage)
            except Exception:
                pass

    def get_stage(self) -> str:
        """获取当前阶段"""
        return self._current_stage_name

    def get_video_name(self) -> str:
        """获取源文件名（不含扩展名），优先 video_path，fallback 到 audio_path"""
        source_path = self.video_path or self.audio_path
        if source_path:
            return Path(source_path).stem
        return "output"

    def get_video_dir(self) -> str:
        """获取源文件目录，优先 video_path，fallback 到 audio_path"""
        source_path = self.video_path or self.audio_path
        if source_path:
            return str(Path(source_path).parent)
        return "."

    def cleanup(self) -> None:
        """清理上下文中的大对象以释放内存。

        释放 Whisper 模型资源（通过上下文管理器），保留结果数据
        （transcription_result 等）供调用方在 pipeline 返回后读取。
        """
        # 通过上下文管理器释放 Whisper 模型
        if hasattr(self, "_model_context") and self._model_context is not None:
            try:
                self._model_context.__exit__(None, None, None)
            except Exception:
                pass
            self._model_context = None
        self.whisper_model_instance = None

        # 释放本地翻译模型缓存（2-4GB 内存）
        try:
            from ..models.local_models import get_local_model_manager

            manager = get_local_model_manager()
            for model_id in list(manager._loaded_models.keys()):
                manager.unload_translation_model(model_id)
        except Exception:
            pass


@dataclass
class ProcessingResult:
    """流水线执行结果"""

    success: bool
    output_path: Optional[str] = None
    error_message: str = ""
    error_type: Optional[str] = None
    error_context: Optional[dict[str, Any]] = None
    error_severity: Optional[str] = None
    context: Optional[ProcessingContext] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_exception(
        cls,
        exc: Exception,
        context: Optional[ProcessingContext] = None,
    ) -> "ProcessingResult":
        """从异常创建失败结果"""
        from ..exceptions import MediaFactoryError

        if isinstance(exc, MediaFactoryError):
            return cls(
                success=False,
                error_message=exc.message,
                error_type=type(exc).__name__,
                error_context=exc.context,
                error_severity=exc.severity,
                context=context,
            )

        return cls(
            success=False,
            error_message=str(exc),
            error_type=type(exc).__name__,
            context=context,
        )
