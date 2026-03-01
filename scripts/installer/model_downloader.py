"""模型下载模块

提供带进度报告的模型下载功能。
支持断点续传和镜像源选择。

注意：ModelType 从 model_registry 导入，保持统一。
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional

# 从统一的模型注册表导入 ModelType
from ..models.model_registry import ModelType


class ModelSource(Enum):
    """模型下载源"""

    OFFICIAL = "https://huggingface.co"
    MIRROR_CHINA = "https://hf-mirror.com"


@dataclass
class ModelInfo:
    """安装程序使用的轻量级模型信息

    与 model_registry.ModelInfo 不同，这是一个简化的数据类，
    仅包含安装程序所需的字段。
    """

    model_id: str  # 完整的模型 ID (如 "Systran/faster-whisper-large-v3")
    alias: str  # 别名 (如 "large-v3")
    model_type: ModelType  # 模型类型（来自 model_registry）
    size_gb: float  # 模型大小 (GB)
    display_name: str  # 显示名称


@dataclass
class ModelDownloadProgress:
    """模型下载进度"""

    stage: str  # 当前阶段: preparing, downloading, verifying, done, error
    progress_percent: int  # 0-100
    message: str  # 当前状态消息
    bytes_downloaded: int = 0
    total_bytes: int = 0
    download_speed: float = 0  # MB/s
    eta_seconds: float = 0  # 预计剩余时间（秒）


# Progress callback type
ProgressCallback = Callable[[ModelDownloadProgress], None]

# 模型下载源
MODEL_SOURCES = {
    "official": "https://huggingface.co",
    "mirror_china": "https://hf-mirror.com",
}


def get_default_models() -> List[ModelInfo]:
    """从注册表获取默认推荐模型列表

    Returns:
        推荐下载的模型列表
    """
    from ..models.model_registry import (
        get_all_translation_models,
        get_whisper_model_info,
    )

    models = []

    # 添加 Whisper 模型
    whisper_info = get_whisper_model_info()
    models.append(
        ModelInfo(
            model_id=whisper_info.huggingface_id,
            alias=whisper_info.model_id.split("/")[-1],
            model_type=ModelType.WHISPER,
            size_gb=whisper_info.model_size_gb,
            display_name=whisper_info.display_name,
        )
    )

    # 添加推荐的翻译模型（内存最小的）
    translation_models = get_all_translation_models()
    if translation_models:
        # 选择内存需求最小的模型作为默认
        best = min(translation_models, key=lambda m: m.runtime_memory_gb)
        models.append(
            ModelInfo(
                model_id=best.huggingface_id,
                alias=best.model_id.split("/")[-1],
                model_type=ModelType.TRANSLATION,
                size_gb=best.model_size_gb,
                display_name=best.display_name,
            )
        )

    return models


class ModelDownloader:
    """模型下载器

    提供带进度报告的模型下载功能。
    支持断点续传和镜像源选择。
    """

    def __init__(self, project_root: Optional[Path] = None):
        """初始化下载器

        Args:
            project_root: 项目根目录，默认自动检测
        """
        if project_root is None:
            # 检测项目根目录
            self.project_root = Path(__file__).parent.parent.parent.parent
        else:
            self.project_root = project_root

        self.models_dir = self.project_root / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def _get_model_path(self, model_info: ModelInfo) -> Path:
        """获取模型的本地保存路径

        使用嵌套目录结构（如 models/Systran/faster-whisper-large-v3/）。

        Args:
            model_info: 模型信息

        Returns:
            模型保存路径
        """
        # 直接使用 model_id（即 huggingface_id）作为路径
        return self.models_dir / model_info.model_id

    def is_model_downloaded(self, model_info: ModelInfo) -> bool:
        """检查模型是否已下载

        Args:
            model_info: 模型信息

        Returns:
            是否已下载
        """
        model_path = self._get_model_path(model_info)
        return model_path.exists() and any(model_path.iterdir())

    def download_model(
        self,
        model_info: ModelInfo,
        source: ModelSource = ModelSource.MIRROR_CHINA,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> bool:
        """下载模型

        Args:
            model_info: 模型信息
            source: 下载源
            progress_callback: 进度回调函数（可选）

        Returns:
            是否成功
        """
        try:
            # 导入下载模块 (从 src 下的核心模块)
            from ..models.model_download import download_model as core_download_model

            # 调用下载函数，使用 model_id（即 huggingface_id）
            core_download_model(
                huggingface_id=model_info.model_id,
                custom_path=None,  # 让核心模块处理路径
                download_source=source.value,
            )

            if progress_callback:
                progress_callback(
                    ModelDownloadProgress(
                        stage="done",
                        progress_percent=100,
                        message=f"{model_info.display_name} 下载完成",
                    )
                )

            return True

        except Exception as e:
            if progress_callback:
                progress_callback(
                    ModelDownloadProgress(
                        stage="error", progress_percent=0, message=f"下载失败: {str(e)}"
                    )
                )
            return False

    def download_models(
        self,
        models: List[ModelInfo],
        source: ModelSource = ModelSource.MIRROR_CHINA,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> bool:
        """下载多个模型

        Args:
            models: 模型信息列表
            source: 下载源
            progress_callback: 进度回调函数

        Returns:
            是否全部成功
        """
        total = len(models)
        success_count = 0

        for i, model_info in enumerate(models):
            # 检查是否已下载
            if self.is_model_downloaded(model_info):
                if progress_callback:
                    progress_callback(
                        ModelDownloadProgress(
                            stage="verifying",
                            progress_percent=int((i + 1) / total * 100),
                            message=f"{model_info.display_name} 已存在，跳过",
                        )
                    )
                success_count += 1
                continue

            # 创建进度包装器
            def model_progress(inner_progress: ModelDownloadProgress):
                if progress_callback:
                    # 计算整体进度
                    base_progress = int(i / total * 100)
                    model_progress_range = int(100 / total)
                    adjusted_percent = base_progress + int(
                        inner_progress.progress_percent / 100 * model_progress_range
                    )
                    progress_callback(
                        ModelDownloadProgress(
                            stage=inner_progress.stage,
                            progress_percent=adjusted_percent,
                            message=f"[{i + 1}/{total}] {inner_progress.message}",
                        )
                    )

            if self.download_model(model_info, source, model_progress):
                success_count += 1

        if progress_callback:
            if success_count == total:
                progress_callback(
                    ModelDownloadProgress(
                        stage="done",
                        progress_percent=100,
                        message=f"所有模型下载完成 ({success_count}/{total})",
                    )
                )
            else:
                progress_callback(
                    ModelDownloadProgress(
                        stage="done",
                        progress_percent=100,
                        message=f"部分模型下载失败 ({success_count}/{total})",
                    )
                )

        return success_count == total

    def get_downloaded_models(self) -> List[str]:
        """获取已下载的模型列表

        Returns:
            模型路径列表
        """
        if not self.models_dir.exists():
            return []

        return [
            str(model_dir.relative_to(self.models_dir))
            for model_dir in self.models_dir.iterdir()
            if model_dir.is_dir() and any(model_dir.iterdir())
        ]

    def delete_model(self, model_info: ModelInfo) -> bool:
        """删除模型

        Args:
            model_info: 模型信息

        Returns:
            是否成功
        """
        model_path = self._get_model_path(model_info)
        try:
            if model_path.exists():
                import shutil

                shutil.rmtree(model_path)
            return True
        except Exception:
            return False


# 导出
__all__ = [
    "ModelDownloader",
    "ModelType",  # 从 model_registry 重新导出
    "ModelSource",
    "ModelInfo",
    "ModelDownloadProgress",
    "get_default_models",  # 替代 DEFAULT_MODELS 常量
    "MODEL_SOURCES",
    "ProgressCallback",
]
