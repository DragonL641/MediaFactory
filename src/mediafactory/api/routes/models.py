"""
模型管理 API 路由

提供模型状态查询、下载、删除等端点。
"""

import asyncio
import functools
import logging
import time
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mediafactory.services.models import ModelStatusService
from mediafactory.api.error_handler import sanitize_error
from mediafactory.i18n import t

logger = logging.getLogger(__name__)
# API 层使用标准 logging，通过 InterceptHandler 自动重定向到 loguru
# 详见 mediafactory.logging.loguru_logger.setup_logging_intercept

router = APIRouter()

# 复用现有服务
_status_service = ModelStatusService()

# 模型状态缓存（60 秒）
_models_status_cache: Dict[str, Any] = None

# 并发下载保护：追踪正在下载的模型
_active_downloads: set[str] = set()
_models_status_cache_time: float = 0
_MODELS_STATUS_CACHE_TTL = 60


def _invalidate_models_status_cache():
    """清除模型状态缓存"""
    global _models_status_cache, _models_status_cache_time
    _models_status_cache = None
    _models_status_cache_time = 0


class DownloadRequest(BaseModel):
    """下载请求"""
    pass


class LLMTestRequest(BaseModel):
    """LLM 测试请求"""
    preset: str = "openai"


@router.get("/status")
async def get_models_status() -> Dict[str, Any]:
    """
    获取所有模型状态

    返回 Whisper、翻译模型、LLM、增强模型、降噪模型的状态信息。
    使用 60 秒缓存减少文件系统检查。
    """
    global _models_status_cache, _models_status_cache_time

    # 检查缓存
    if _models_status_cache and (time.time() - _models_status_cache_time) < _MODELS_STATUS_CACHE_TTL:
        return _models_status_cache

    whisper_status = _status_service.get_whisper_status()
    translation_status = _status_service.get_translation_status()
    llm_status = _status_service.get_llm_status()

    # 获取翻译模型详情
    translation_models = _status_service.get_translation_model_statuses()

    # 一次性获取 config，传递给子函数
    from mediafactory.config import get_config
    config = get_config()

    enhancement_models = _get_enhancement_model_statuses(config)
    denoise_models = _get_denoise_model_statuses(config)

    # 获取 Whisper 模型详情列表
    whisper_models = _get_whisper_model_statuses()

    result = {
        "whisper": {
            "name": whisper_status.name,
            "loaded": whisper_status.loaded,
            "available": whisper_status.available,
            "enabled": whisper_status.enabled,
            "models": whisper_models,
        },
        "translation": {
            "name": translation_status.name,
            "loaded": translation_status.loaded,
            "available": translation_status.available,
            "enabled": translation_status.enabled,
            "models": translation_models,
        },
        "llm": {
            "name": llm_status.name,
            "loaded": llm_status.loaded,
            "available": llm_status.available,
            "enabled": llm_status.enabled,
            "config": _status_service.get_llm_config(),
        },
        "enhancement": {
            "name": "Real-ESRGAN",
            "models": enhancement_models,
        },
        "denoise": {
            "name": "NAFNet",
            "models": denoise_models,
        },
    }

    # 更新缓存
    _models_status_cache = result
    _models_status_cache_time = time.time()

    return result


def _get_model_statuses_by_type(model_type) -> List[Dict[str, Any]]:
    """从 MODEL_REGISTRY 获取指定类型模型的状态列表"""
    from mediafactory.models.model_registry import (
        MODEL_REGISTRY,
        ModelType,
        is_model_downloaded,
        is_model_complete,
    )

    def _format_size(mb: int) -> str:
        if mb >= 1024:
            return f"{mb // 1024} GB"
        return f"{mb} MB"

    result = []
    for model_id, info in MODEL_REGISTRY.items():
        if info.model_type != model_type:
            continue
        downloaded = is_model_downloaded(model_id)
        result.append({
            "id": model_id,
            "name": info.display_name,
            "purpose": info.purpose or info.display_name,
            "size": _format_size(info.model_size_mb),
            "memory": _format_size(info.runtime_memory_mb),
            "vram": _format_size(info.runtime_vram_mb) if info.runtime_vram_mb else "",
            "description": info.description or "",
            "downloaded": downloaded,
            "complete": is_model_complete(model_id) if downloaded else False,
        })
    return result


def _get_whisper_model_statuses() -> List[Dict[str, Any]]:
    """获取 Whisper 模型状态列表"""
    from mediafactory.models.model_registry import ModelType
    return _get_model_statuses_by_type(ModelType.WHISPER)


def _get_enhancement_model_statuses(config) -> List[Dict[str, Any]]:
    """获取 Real-ESRGAN 增强模型状态"""
    from mediafactory.models.model_registry import ModelType
    return _get_model_statuses_by_type(ModelType.SUPER_RESOLUTION)


def _get_denoise_model_statuses(config) -> List[Dict[str, Any]]:
    """获取 NAFNet 降噪模型状态"""
    from mediafactory.models.model_registry import ModelType
    return _get_model_statuses_by_type(ModelType.DENOISE)


@router.get("/whisper")
async def get_whisper_status() -> Dict[str, Any]:
    """获取 Whisper 模型状态"""
    status = _status_service.get_whisper_status()
    return {
        "name": status.name,
        "loaded": status.loaded,
        "available": status.available,
        "enabled": status.enabled,
    }


@router.get("/translation")
async def get_translation_status() -> Dict[str, Any]:
    """获取翻译模型状态"""
    status = _status_service.get_translation_status()
    models = _status_service.get_translation_model_statuses()
    return {
        "name": status.name,
        "loaded": status.loaded,
        "available": status.available,
        "enabled": status.enabled,
        "models": models,
    }


@router.get("/llm")
async def get_llm_status() -> Dict[str, Any]:
    """获取 LLM 状态"""
    status = _status_service.get_llm_status()
    config = _status_service.get_llm_config()
    return {
        "name": status.name,
        "loaded": status.loaded,
        "available": status.available,
        "enabled": status.enabled,
        "config": config,
    }


@router.get("/readiness")
async def get_readiness() -> Dict[str, Any]:
    """获取任务前置条件就绪状态"""
    return _status_service.get_readiness()


@router.post("/download/{model_id:path}")
async def start_model_download(
    model_id: str,
    request: DownloadRequest = DownloadRequest(),
):
    """
    启动模型下载

    支持通过镜像源下载。
    """
    from mediafactory.api.main import get_task_manager
    from mediafactory.api.schemas import TaskConfig, TaskType
    from mediafactory.api.websocket import manager as ws_manager

    # 并发下载保护：同一模型或任何下载进行中时拒绝
    if model_id in _active_downloads:
        raise HTTPException(
            status_code=409,
            detail=t("task.downloadAlreadyInProgress", modelId=model_id),
        )
    if _active_downloads:
        raise HTTPException(
            status_code=409,
            detail=t("task.anotherDownloadInProgress"),
        )

    _active_downloads.add(model_id)

    # 从配置读取下载源
    from mediafactory.config import get_config
    download_config = get_config()
    download_source = download_config.model.download_source
    endpoint = None if download_source == "https://huggingface.co" else download_source
    hf_token = download_config.model.hf_token or None

    # 启动下载任务
    task_manager = get_task_manager()

    config = TaskConfig(
        task_type=TaskType.DOWNLOAD,
        input_path=model_id,
    )

    task_id = await task_manager.create_task(
        config, name=t("task.downloadingModel", modelId=model_id)
    )

    # 后台执行下载
    async def _execute_download_task():
        """执行模型下载任务"""
        from mediafactory.models.model_download import download_model
        from mediafactory.api.schemas import TaskStatus as TS, TaskResult as TR

        loop = asyncio.get_running_loop()

        # 更新任务状态为 RUNNING
        await task_manager.update_task_status(task_id, TS.RUNNING)

        async def _progress_callback(progress: float, msg: str = ""):
            await ws_manager.broadcast_progress(
                task_id=task_id,
                status="downloading",
                progress=progress * 100,
                message=msg,
                stage="download",
            )

        try:
            _last_progress_time = [0.0]  # 可变容器，供闭包修改
            _PROGRESS_THROTTLE_SEC = 0.5  # 最小 500ms 间隔

            def sync_progress(p: float, m: str = ""):
                # 从下载线程安全地调度到主事件循环
                import time as _time
                now = _time.monotonic()
                # 节流：非 100% 进度时，限制最小间隔
                if p < 0.99 and (now - _last_progress_time[0]) < _PROGRESS_THROTTLE_SEC:
                    return
                _last_progress_time[0] = now
                loop.call_soon_threadsafe(
                    lambda: asyncio.ensure_future(_progress_callback(p, m))
                )

            await loop.run_in_executor(
                None,
                functools.partial(
                    download_model,
                    model_id,
                    download_source=endpoint,
                    progress_callback=sync_progress,
                ),
            )

            _invalidate_models_status_cache()

            # 更新任务状态为 COMPLETED
            await task_manager.update_task_status(
                task_id, TS.COMPLETED,
                progress=100, stage="download",
                result=TR(task_id=task_id, success=True, output_path=f"models/{model_id}"),
            )

            await ws_manager.broadcast_task_complete(
                task_id=task_id,
                success=True,
                output_path=f"models/{model_id}",
            )

        except Exception as e:
            logger.exception(f"Download failed: {e}")
            # 更新任务状态为 FAILED
            await task_manager.update_task_status(
                task_id, TS.FAILED, stage="download",
                result=TR(
                    task_id=task_id, success=False, error=sanitize_error(e),
                    error_type=type(e).__name__,
                ),
            )
            await ws_manager.broadcast_task_complete(
                task_id=task_id,
                success=False,
                error=sanitize_error(e),
            )
        finally:
            _active_downloads.discard(model_id)

    # 启动后台任务
    asyncio.create_task(_execute_download_task())

    return {
        "task_id": task_id,
        "status": "pending",
        "message": t("task.downloadCreated", modelId=model_id),
    }


@router.delete("/{model_id:path}")
async def delete_model(model_id: str):
    """删除模型"""
    from mediafactory.models.model_download import delete_model as delete_model_func

    success, error = delete_model_func(model_id)

    if not success:
        raise HTTPException(status_code=400, detail=error)

    _invalidate_models_status_cache()
    return {"success": True, "message": t("task.modelDeleted", modelId=model_id)}


@router.post("/llm/test")
async def test_llm_connection(request: LLMTestRequest):
    """
    测试 LLM 连接

    发送测试请求到指定的 LLM 预设。
    """
    result = await _status_service.test_llm_connection(request.preset)
    return result


@router.post("/llm/test-all")
async def test_all_llm_connections():
    """测试所有 LLM 预设连接"""
    results = await _status_service.test_all_llm_connections()
    return results
