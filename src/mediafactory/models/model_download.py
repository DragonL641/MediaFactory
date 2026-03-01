"""模型下载核心功能模块

提供统一的模型下载、检测、删除功能。
此模块在 src 下，可被业务代码和脚本共同使用。
"""

import shutil
from pathlib import Path
from typing import Optional, Callable, Tuple

from huggingface_hub import snapshot_download, HfApi

from .model_registry import (
    MODEL_REGISTRY,
    ModelType,
    get_model_info,
)
from ..config import get_app_root_dir
from ..logging import log_error, log_exception, log_info


def get_models_dir() -> Path:
    """获取 models 目录路径。"""
    return get_app_root_dir() / "models"


def get_model_total_size(
    huggingface_id: str, endpoint: Optional[str] = None
) -> Optional[int]:
    """从 HuggingFace API 获取模型总大小。

    Args:
        huggingface_id: HuggingFace 模型 ID（如 "google/madlad400-3b-mt"）
        endpoint: 可选的镜像源 URL

    Returns:
        模型总大小（字节），如果获取失败则返回 None
    """
    try:
        api = HfApi(endpoint=endpoint)
        files = list(
            api.list_repo_tree(
                repo_id=huggingface_id, repo_type="model", recursive=True
            )
        )
        # 过滤掉目录，只保留文件
        files = [f for f in files if hasattr(f, "size") and f.size is not None]
        return sum(f.size for f in files) if files else None
    except Exception as e:
        log_error(f"Failed to get model total size for {huggingface_id}: {e}")
        return None


def get_downloaded_size(model_path: Path) -> int:
    """计算本地已下载模型目录的总大小。

    Args:
        model_path: 模型目录路径

    Returns:
        已下载文件的总大小（字节）
    """
    if not model_path.exists():
        return 0

    total_size = 0
    for f in model_path.rglob("*"):
        # 跳过 .cache 子目录和目录
        if f.is_file() and ".cache" not in f.parts:
            try:
                total_size += f.stat().st_size
            except OSError:
                pass  # 忽略无法访问的文件
    return total_size


def is_model_complete(huggingface_id: str) -> bool:
    """验证模型是否完整下载。

    检查模型目录是否存在，以及关键文件是否存在。

    Args:
        huggingface_id: HuggingFace 模型 ID

    Returns:
        True 如果模型完整，否则 False
    """
    model_path = get_models_dir() / huggingface_id

    # 目录必须存在
    if not model_path.exists():
        return False

    # 根据模型类型检查关键文件
    model_info = get_model_info(huggingface_id)
    if model_info is None:
        # 未知模型，只检查目录存在
        return True

    # 检查 config.json 是否存在（所有模型都需要）
    if not (model_path / "config.json").exists():
        return False

    if model_info.model_type == ModelType.WHISPER:
        # Whisper 模型：需要 model.bin 或 model.safetensors
        has_model_file = (model_path / "model.bin").exists() or (
            model_path / "model.safetensors"
        ).exists()
        return has_model_file
    else:
        # 翻译模型：需要 model.safetensors 或 pytorch_model.bin
        has_model_file = (model_path / "model.safetensors").exists() or (
            model_path / "pytorch_model.bin"
        ).exists()
        # GGUF 模型可能没有上述文件，检查 GGUF 文件
        if not has_model_file:
            gguf_files = list(model_path.glob("*.gguf"))
            has_model_file = len(gguf_files) > 0
        return has_model_file


def is_model_downloaded(huggingface_id: str) -> bool:
    """检查模型是否已下载。

    使用嵌套目录结构（如 models/Systran/faster-whisper-large-v3/）。

    Args:
        huggingface_id: HuggingFace 模型 ID

    Returns:
        True 如果模型已下载
    """
    models_dir = get_models_dir()
    # 直接使用 huggingface_id 作为路径（保留斜杠）
    model_path = models_dir / huggingface_id

    return model_path.exists()


def download_model(
    huggingface_id: str,
    custom_path: Optional[str] = None,
    download_source: Optional[str] = None,
) -> Path:
    """从注册表下载模型。

    Args:
        huggingface_id: HuggingFace 模型 ID（如 "Systran/faster-whisper-large-v3"）
        custom_path: 自定义保存目录
        download_source: 下载源 URL

    Returns:
        下载后的模型路径

    Raises:
        ValueError: 模型 ID 未知
        Exception: 下载失败
    """
    model_info = get_model_info(huggingface_id)
    if model_info is None:
        raise ValueError(f"Unknown model ID '{huggingface_id}'")

    # 确定本地保存路径（使用嵌套目录结构）
    if custom_path is None:
        # 直接使用 huggingface_id 作为子目录（保留斜杠）
        local_path = get_models_dir() / huggingface_id
    else:
        local_path = Path(custom_path).absolute()

    # 处理下载源
    endpoint = None if download_source == "https://huggingface.co" else download_source

    # 使用 snapshot_download 直接下载整个仓库
    # 这是 HuggingFace 官方推荐的方式，会自动处理所有文件
    snapshot_download(
        repo_id=huggingface_id,
        local_dir=str(local_path),
        endpoint=endpoint,
    )

    # 下载成功后更新配置文件
    _update_config_after_download(huggingface_id, model_info.model_type)

    return local_path


def delete_model(huggingface_id: str) -> Tuple[bool, str]:
    """删除已下载的模型。

    Args:
        huggingface_id: HuggingFace 模型 ID

    Returns:
        (success, error_message) - 成功时 error_message 为空字符串
    """
    model_info = get_model_info(huggingface_id)
    if model_info is None:
        error_msg = f"Unknown model ID: {huggingface_id}"
        log_error(f"delete_model failed: {error_msg}")
        return False, error_msg

    # 使用嵌套目录结构
    models_dir = get_models_dir()
    model_path = models_dir / huggingface_id

    if not model_path.exists():
        error_msg = f"Model not found: {huggingface_id}"
        log_error(f"delete_model failed: {error_msg}")
        return False, error_msg

    try:
        shutil.rmtree(model_path)
        log_info(f"Model deleted: {huggingface_id}")
    except PermissionError as e:
        error_msg = f"Permission denied: {e}"
        log_error(f"Failed to delete model {huggingface_id}: {error_msg}")
        return False, error_msg
    except OSError as e:
        error_msg = f"OS error: {e}"
        log_error(f"Failed to delete model {huggingface_id}: {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        log_exception(f"Failed to delete model {huggingface_id}")
        return False, error_msg

    # 删除成功后更新配置文件
    _update_config_after_delete(huggingface_id, model_info.model_type)
    return True, ""


def get_all_model_statuses() -> dict[str, bool]:
    """获取所有模型的下载状态。

    Returns:
        {huggingface_id: is_downloaded} 字典
    """
    statuses = {}
    for huggingface_id, model_info in MODEL_REGISTRY.items():
        statuses[huggingface_id] = is_model_downloaded(huggingface_id)
    return statuses


def _update_config_after_download(huggingface_id: str, model_type: ModelType) -> None:
    """下载成功后更新配置文件中的模型列表。"""
    from ..config import get_config_manager

    config_manager = get_config_manager()
    config = config_manager.config

    if model_type == ModelType.TRANSLATION:
        models_list = list(config.model.available_translation_models)
        if huggingface_id not in models_list:
            models_list.append(huggingface_id)
            config_manager.update(model__available_translation_models=models_list)
    elif model_type == ModelType.WHISPER:
        models_list = list(config.model.whisper_models)
        if huggingface_id not in models_list:
            models_list.append(huggingface_id)
            config_manager.update(model__whisper_models=models_list)


def _update_config_after_delete(huggingface_id: str, model_type: ModelType) -> None:
    """删除成功后更新配置文件中的模型列表。"""
    from ..config import get_config_manager

    config_manager = get_config_manager()
    config = config_manager.config

    if model_type == ModelType.TRANSLATION:
        models_list = list(config.model.available_translation_models)
        if huggingface_id in models_list:
            models_list.remove(huggingface_id)
            config_manager.update(model__available_translation_models=models_list)
    elif model_type == ModelType.WHISPER:
        models_list = list(config.model.whisper_models)
        if huggingface_id in models_list:
            models_list.remove(huggingface_id)
            config_manager.update(model__whisper_models=models_list)


__all__ = [
    "get_models_dir",
    "get_model_total_size",
    "get_downloaded_size",
    "is_model_complete",
    "is_model_downloaded",
    "download_model",
    "delete_model",
    "get_all_model_statuses",
]
