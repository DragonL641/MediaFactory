"""模型下载核心功能模块

提供统一的模型下载、检测、删除功能。
此模块在 src 下，可被业务代码和脚本共同使用。
"""

import shutil
import time
from pathlib import Path
from typing import Optional, Callable, Tuple

# Lazy import for huggingface_hub - only needed for download operations
# This allows the module to be imported without ML dependencies

from .model_registry import (
    MODEL_REGISTRY,
    DownloadMode,
    ModelType,
    get_enhancement_models_dir,
    get_model_info,
    get_model_local_path,
    get_models_base_dir,  # 使用 model_registry 中的统一路径函数
)
from ..logging import log_error, log_exception, log_info

# 重试配置
MAX_RETRIES = 3  # 最大重试次数
RETRY_DELAY = 5  # 重试间隔（秒）


def get_models_dir() -> Path:
    """获取 models 目录路径。

    注意：此函数是对 model_registry.get_models_base_dir() 的兼容性封装。
    新代码应直接使用 model_registry.get_models_base_dir()。
    """
    return get_models_base_dir()


def get_model_total_size(
    huggingface_id: str, endpoint: Optional[str] = None
) -> Optional[int]:
    """从 HuggingFace API 获取模型总大小。

    Args:
        huggingface_id: HuggingFace 模型 ID（如 "facebook/m2m100_1.2B"）
        endpoint: 可选的镜像源 URL

    Returns:
        模型总大小（字节），如果获取失败则返回 None
    """
    try:
        from huggingface_hub import HfApi

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
    """计算本地已下载模型目录的总大小（包括 .cache 中的临时文件）。

    Args:
        model_path: 模型目录路径

    Returns:
        已下载文件的总大小（字节），包括正在下载中的临时文件
    """
    if not model_path.exists():
        return 0

    total_size = 0
    for f in model_path.rglob("*"):
        # 只计算文件，跳过目录
        if not f.is_file():
            continue
        try:
            # 包含 .cache 目录中的 .incomplete 临时文件
            # huggingface_hub 下载大文件时会先写入 .cache，完成后才移动
            total_size += f.stat().st_size
        except OSError:
            pass  # 忽略无法访问的文件
    return total_size


def _patch_hf_tqdm(callback):
    """上下文管理器：临时替换 huggingface_hub 下载模块的进度条，将字节级进度转发到 callback。

    hf_hub_download 在 v0.36 不支持 tqdm_class 参数，
    通过 monkey-patch _get_progress_bar_context 来捕获下载进度。
    """
    from contextlib import nullcontext

    if callback is None:
        return nullcontext()

    import huggingface_hub.file_download as _fd
    from huggingface_hub.utils.tqdm import tqdm as _hf_tqdm
    import io as _io

    _original_fn = _fd._get_progress_bar_context

    class _ProgressTqdm(_hf_tqdm):
        """自定义 tqdm，每次 update 时通过 callback 上报下载进度。"""

        def update(self, n=1):
            result = super().update(n)
            if self.total and self.total > 0:
                pct = min(self.n / self.total, 0.99)
                msg = f"{self.n >> 20} MB / {self.total >> 20} MB"
                callback(pct, msg)
            return result

    def _patched_get_ctx(
        *,
        desc,
        log_level,
        total=None,
        initial=0,
        unit="B",
        unit_scale=True,
        name=None,
        _tqdm_bar=None,
    ):
        if _tqdm_bar is not None:
            return nullcontext(_tqdm_bar)
        return _ProgressTqdm(
            unit=unit,
            unit_scale=unit_scale,
            total=total,
            initial=initial,
            desc=desc,
            name=name,
            disable=False,
            file=_io.StringIO(),  # 抑制终端输出
        )

    _fd._get_progress_bar_context = _patched_get_ctx

    class _Patcher:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            _fd._get_progress_bar_context = _original_fn

    return _Patcher()


def download_model(
    huggingface_id: str,
    custom_path: Optional[str] = None,
    download_source: Optional[str] = None,
    progress_callback: Optional[Callable] = None,
    hf_token: Optional[str] = None,
) -> Path:
    """从注册表下载模型（带重试机制）。

    Args:
        huggingface_id: HuggingFace 模型 ID（如 "Systran/faster-whisper-large-v3"）
        custom_path: 自定义保存目录
        download_source: 下载源 URL
        progress_callback: 可选的进度回调函数 (progress: float, message: str)

    Returns:
        下载后的模型路径

    Raises:
        ValueError: 模型 ID 未知
        Exception: 下载失败（所有重试后）
    """
    model_info = get_model_info(huggingface_id)
    if model_info is None:
        raise ValueError(f"Unknown model ID '{huggingface_id}'")

    is_file_mode = model_info.download_mode == DownloadMode.FILE
    log_info(
        f"Starting download: {huggingface_id} ({'file' if is_file_mode else 'repo'} mode)..."
    )

    # 确定本地保存路径
    if custom_path is not None:
        local_path = Path(custom_path).absolute()
    elif is_file_mode:
        # 单文件模型保存到 enhancement 目录
        enhancement_dir = get_enhancement_models_dir()
        enhancement_dir.mkdir(parents=True, exist_ok=True)
        filename = (
            model_info.local_filename
            or model_info.huggingface_filename
            or huggingface_id
        )
        local_path = enhancement_dir / filename
    else:
        # 仓库模型使用 huggingface_id 作为子目录（保留斜杠）
        local_path = get_models_dir() / huggingface_id

    # 处理下载源
    endpoint = None if download_source == "https://huggingface.co" else download_source

    # 带重试机制的下载（在 tqdm monkey-patch 作用域内执行）
    last_error = None
    with _patch_hf_tqdm(progress_callback):
        for attempt in range(MAX_RETRIES):
            if attempt > 0:
                log_info(
                    f"Retrying download ({attempt + 1}/{MAX_RETRIES}) for {huggingface_id}..."
                )
                # 重试前通知前端
                if progress_callback is not None:
                    progress_callback(0.0, f"Retrying ({attempt + 1}/{MAX_RETRIES})...")
                time.sleep(RETRY_DELAY)

            try:
                if is_file_mode:
                    # 单文件模型：使用 hf_hub_download 下载指定文件
                    from huggingface_hub import hf_hub_download

                    hf_hub_download(
                        repo_id=model_info.huggingface_repo,
                        filename=model_info.huggingface_filename,
                        local_dir=str(get_enhancement_models_dir()),
                        endpoint=endpoint,
                        token=hf_token or None,
                    )
                else:
                    # 仓库模型：使用 snapshot_download 下载整个仓库
                    from huggingface_hub import snapshot_download

                    snapshot_download(
                        repo_id=huggingface_id,
                        local_dir=str(local_path),
                        endpoint=endpoint,
                        max_workers=4,
                        token=hf_token or None,
                    )

                # 下载成功，通知完成
                if progress_callback is not None:
                    progress_callback(1.0, "Download complete")

                log_info(f"Download complete: {huggingface_id}")

                # 下载成功后更新配置文件
                _update_config_after_download(huggingface_id, model_info.model_type)

                return local_path

            except Exception as ex:
                last_error = ex
                log_error(
                    f"Download failed for {huggingface_id} (attempt {attempt + 1}/{MAX_RETRIES}): {ex}"
                )

                # Gated repo 权限错误不重试（重试不会改变结果）
                err_msg = str(ex)
                if (
                    "not in the authorized list" in err_msg
                    or "gated repo" in err_msg.lower()
                ):
                    raise Exception(
                        f"Access denied for {huggingface_id}. "
                        f"This is a gated model — please: "
                        f"1) Accept terms at https://huggingface.co/{huggingface_id} ; "
                        f"2) if this model has dependencies (e.g. stable-ts segmentation-3.0), accept their terms"
                        f"3) Ensure HuggingFace Token is configured in Settings > HuggingFace Hub"
                    )

                # 非最后一次重试，继续尝试
                if attempt < MAX_RETRIES - 1:
                    continue

    # 所有重试都失败，清理中间文件后抛出异常
    _cleanup_failed_download(local_path, is_file_mode)
    raise Exception(f"Download failed after {MAX_RETRIES} retries: {last_error}")


def _cleanup_failed_download(model_path: Path, is_file_mode: bool) -> None:
    """清理下载失败后残留的中间文件。

    repo 模式：删除 .cache 目录和空模型目录
    file 模式：删除不完整的文件
    """
    try:
        if is_file_mode:
            # 单文件模式：删除不完整的文件
            if model_path.exists():
                model_path.unlink(missing_ok=True)
                log_info(f"Cleaned incomplete file: {model_path}")
        else:
            # 仓库模式：先清理 .cache（huggingface_hub 临时文件），再删除空目录
            cache_dir = model_path / ".cache"
            if cache_dir.exists():
                shutil.rmtree(cache_dir, ignore_errors=True)
                log_info(f"Cleaned cache directory: {cache_dir}")
            # 删除整个模型目录（含所有残留文件）
            if model_path.exists():
                shutil.rmtree(model_path, ignore_errors=True)
                log_info(f"Cleaned failed download directory: {model_path}")
    except Exception as e:
        # 清理失败不应阻断异常上报，仅记录日志
        log_error(f"Failed to clean up download artifacts: {e}")


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

    # 根据下载模式确定模型路径
    if model_info.download_mode == DownloadMode.FILE:
        # 单文件模型（如 Real-ESRGAN、NAFNet）
        model_path = get_model_local_path(huggingface_id)
        is_file_mode = True
    else:
        # 仓库模型（如 Whisper、翻译模型）
        models_dir = get_models_dir()
        model_path = models_dir / huggingface_id
        is_file_mode = False

    if model_path is None or not model_path.exists():
        error_msg = f"Model not found: {huggingface_id}"
        log_error(f"delete_model failed: {error_msg}")
        return False, error_msg

    # 尝试删除，带重试机制（处理文件被占用的情况）
    max_retries = 3
    retry_delay = 1  # 秒

    for attempt in range(max_retries):
        try:
            if is_file_mode:
                # 单文件模式：直接删除文件
                model_path.unlink()
            else:
                # 仓库模式：清理缓存后删除目录
                cache_dir = model_path / ".cache"
                if cache_dir.exists():
                    try:
                        shutil.rmtree(cache_dir)
                        log_info(f"Cleaned cache directory for {huggingface_id}")
                    except PermissionError:
                        pass
                shutil.rmtree(model_path)

            log_info(f"Model deleted: {huggingface_id}")
            _update_config_after_delete(huggingface_id, model_info.model_type)

            # 清理 HuggingFace 全局缓存（非关键操作，失败不影响删除流程）
            hf_repo_id = model_info.huggingface_repo if is_file_mode else huggingface_id
            _cleanup_hf_global_cache(hf_repo_id)

            return True, ""

        except PermissionError as e:
            if attempt < max_retries - 1:
                log_info(
                    f"Delete failed (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s..."
                )
                time.sleep(retry_delay)
                retry_delay *= 2  # 指数退避
            else:
                error_msg = f"Permission denied: {e}"
                log_error(f"Failed to delete model {huggingface_id}: {error_msg}")
                if ".incomplete" in str(e) or "being used by another process" in str(e):
                    error_msg = f"模型正在下载或被其他进程占用，请稍后重试。\n详情: {e}"
                return False, error_msg
        except OSError as e:
            error_msg = f"OS error: {e}"
            log_error(f"Failed to delete model {huggingface_id}: {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            log_exception(f"Failed to delete model {huggingface_id}")
            return False, error_msg

    return False, "Unknown error"


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


def _cleanup_hf_global_cache(repo_id: str) -> None:
    """清理 HuggingFace 全局缓存中指定仓库的数据。

    当使用 hf_hub_download / snapshot_download 下载模型时，
    即使指定了 local_dir，HF Hub 仍会在全局缓存中保留数据（blob + 元数据）。
    此函数在模型删除后清理这些残留缓存，释放磁盘空间。
    非关键操作，失败不影响删除流程。
    """
    try:
        from huggingface_hub.constants import HF_HUB_CACHE

        # HF 缓存目录命名规则：models--{org}--{repo}
        cache_repo_dir = Path(HF_HUB_CACHE) / f"models--{repo_id.replace('/', '--')}"
        if cache_repo_dir.exists():
            shutil.rmtree(cache_repo_dir)
            log_info(f"Cleaned HuggingFace global cache for {repo_id}")
    except Exception as e:
        log_info(f"Could not clean HF cache for {repo_id} (non-critical): {e}")


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
    elif model_type in (ModelType.SUPER_RESOLUTION, ModelType.DENOISE):
        # 增强模型删除后无需特殊配置更新
        pass


__all__ = [
    "get_models_dir",
    "get_model_total_size",
    "get_downloaded_size",
    "download_model",
    "delete_model",
]
